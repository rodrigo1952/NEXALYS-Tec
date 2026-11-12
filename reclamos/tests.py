"""Libro de Reclamaciones virtual: hoja con correlativo, constancia, la tienda responde en 15 días hábiles."""
from datetime import date
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from administracion.models import AccionAdmin
from tiendas.models import Tienda
from tiendas.tests import crear_tienda

from .models import Reclamo

CLAVE = "ClaveSegura#2026"


def datos(**cambios):
    base = {
        "dirigido_a": "nexalys", "nombre": "Luis Mamani Quispe", "documento_tipo": "dni", "documento_numero": "45678912",
        "domicilio": "Jr. Lima 120, Quillabamba", "telefono": "984123456", "correo": "luis@ejemplo.com",
        "bien": "producto", "descripcion_bien": "Audífonos Xiaomi Redmi Buds 4", "monto": "89.90",
        "comprobante": "B001-120", "fecha_compra": "2026-11-02", "tipo": "reclamo",
        "detalle": "El audífono derecho dejó de sonar a la semana.", "pedido": "Cambio por uno nuevo.", "acepto": "on",
    }
    base.update(cambios)
    return base


class PresentarHojaTests(TestCase):
    def setUp(self):
        self.tienda = crear_tienda()
        self.tienda.ruc = "10456789123"
        self.tienda.save()
        self.url = reverse("reclamos:libro")

    def test_enlace_permanente_en_el_pie(self):
        for url in (reverse("inicio"), reverse("catalogo:catalogo"), reverse("privacidad")):
            self.assertContains(self.client.get(url), f'href="{self.url}"', msg_prefix=url)

    def test_formulario_con_las_tiendas_activas(self):
        crear_tienda("t2", "Tienda Suspendida", "922222222", estado=Tienda.Estado.SUSPENDIDA)
        respuesta = self.client.get(self.url + f"?tienda={self.tienda.pk}")
        self.assertContains(respuesta, f'<option value="{self.tienda.pk}" selected>Tienda: Tienda Uno</option>')
        self.assertNotContains(respuesta, "Tienda Suspendida")
        self.assertContains(respuesta, "no impide acudir a otras vías de solución de controversias")

    @override_settings(PRIVACIDAD_TITULAR="NEXALYS Tec E.I.R.L.", PRIVACIDAD_DOCUMENTO="20601234567", PRIVACIDAD_DIRECCION="Quillabamba")
    def test_hoja_contra_nexalys_con_correlativo_y_constancia(self):
        with mock.patch("django.utils.timezone.localdate", return_value=date(2026, 11, 13)):
            respuesta = self.client.post(self.url, datos(), follow=True)
        hoja = Reclamo.objects.get()
        self.assertEqual((hoja.proveedor_clave, hoja.numero, hoja.codigo[:6]), ("nexalys", 1, "000001"))
        self.assertEqual(hoja.proveedor_nombre, "NEXALYS Tec E.I.R.L.")
        self.assertEqual(hoja.proveedor_ruc, "20601234567")
        self.assertEqual(hoja.vence, date(2026, 12, 4))  # 15 días hábiles desde el viernes 13/11
        self.assertContains(respuesta, f"Tu hoja N.° {hoja.codigo} fue registrada.")
        self.assertEqual(mail.outbox[0].to, ["luis@ejemplo.com"])
        self.assertIn(f"HOJA DE RECLAMACIÓN N.° {hoja.codigo}", mail.outbox[0].body)
        self.assertIn("El audífono derecho dejó de sonar", mail.outbox[0].body)
        self.assertIn("INDECOPI", mail.outbox[0].body)

    def test_hoja_contra_una_tienda_avisa_a_la_tienda(self):
        self.client.post(self.url, datos(dirigido_a=str(self.tienda.pk)))
        hoja = Reclamo.objects.get()
        self.assertEqual((hoja.tienda, hoja.proveedor_nombre, hoja.proveedor_ruc), (self.tienda, "Tienda Uno", "10456789123"))
        self.assertEqual(hoja.proveedor_clave, f"tienda-{self.tienda.pk}")
        self.assertEqual([m.to for m in mail.outbox], [["luis@ejemplo.com"], [self.tienda.usuario.email]])

    def test_correlativo_por_proveedor(self):
        otra = crear_tienda("t2", "Tienda Dos", "922222222")
        for destino in ("nexalys", str(self.tienda.pk), str(self.tienda.pk), str(otra.pk)):
            Reclamo.objects.create(
                tienda=None if destino == "nexalys" else Tienda.objects.get(pk=destino), proveedor_nombre="x",
                nombre="A", documento_numero="12345678", domicilio="x", correo="a@ejemplo.com",
                descripcion_bien="x", detalle="x", pedido="x", vence=date(2026, 12, 1),
            )
        numeros = list(Reclamo.objects.order_by("pk").values_list("proveedor_clave", "numero"))
        self.assertEqual(numeros, [("nexalys", 1), (f"tienda-{self.tienda.pk}", 1), (f"tienda-{self.tienda.pk}", 2), (f"tienda-{otra.pk}", 1)])

    def test_validaciones(self):
        respuesta = self.client.post(self.url, datos(documento_numero="123", menor_de_edad="on", apoderado="", acepto=""))
        self.assertContains(respuesta, "El DNI tiene 8 dígitos.")
        self.assertContains(respuesta, "escribe el nombre de tu padre, madre o apoderado")
        self.assertContains(respuesta, "Marca la casilla para enviar la hoja.")
        self.assertFalse(Reclamo.objects.exists())

    def test_maximo_3_por_hora(self):
        for _ in range(3):
            self.client.post(self.url, datos())
        self.assertContains(self.client.post(self.url, datos()), "Demasiados intentos.")
        self.assertEqual(Reclamo.objects.count(), 3)

    def test_la_hoja_no_la_ve_cualquiera(self):
        self.client.post(self.url, datos())
        hoja = Reclamo.objects.get()
        self.assertEqual(self.client.get(reverse("reclamos:hoja", args=[hoja.pk])).status_code, 200)
        otro = self.client_class()
        self.assertEqual(otro.get(reverse("reclamos:hoja", args=[hoja.pk])).status_code, 403)


class ResponderTests(TestCase):
    def setUp(self):
        self.tienda = crear_tienda()
        self.client.post(reverse("reclamos:libro"), datos(dirigido_a=str(self.tienda.pk)))
        self.client.post(reverse("reclamos:libro"), datos(correo="ana@ejemplo.com"))
        self.de_tienda = Reclamo.objects.get(tienda=self.tienda)
        self.de_nexalys = Reclamo.objects.get(proveedor_clave="nexalys")
        mail.outbox.clear()
        self.client.logout()
        self.client.session.flush()

    def test_la_tienda_ve_solo_las_suyas_y_responde(self):
        self.client.force_login(self.tienda.usuario)
        lista = self.client.get(reverse("reclamos:tienda_lista"))
        self.assertContains(lista, self.de_tienda.codigo)
        self.assertContains(lista, "Luis Mamani Quispe")
        self.assertNotContains(lista, "ana@ejemplo.com")
        self.assertEqual(self.client.get(reverse("reclamos:tienda_detalle", args=[self.de_nexalys.pk])).status_code, 404)
        url = reverse("reclamos:tienda_detalle", args=[self.de_tienda.pk])
        respuesta = self.client.post(url, {"respuesta": "Le cambiamos los audífonos por unos nuevos el 15/11."}, follow=True)
        self.assertContains(respuesta, "Respuesta guardada y enviada a luis@ejemplo.com.")
        self.de_tienda.refresh_from_db()
        self.assertEqual(self.de_tienda.estado, Reclamo.Estado.RESPONDIDO)
        self.assertIn("Le cambiamos los audífonos", mail.outbox[-1].body)
        # No se responde dos veces.
        self.client.post(url, {"respuesta": "Otra respuesta distinta de la primera."})
        self.de_tienda.refresh_from_db()
        self.assertIn("Le cambiamos", self.de_tienda.respuesta)

    def test_globo_en_el_panel_de_la_tienda(self):
        self.client.force_login(self.tienda.usuario)
        respuesta = self.client.get(reverse("tiendas:panel"))
        self.assertContains(respuesta, '<span class="badge rounded-pill text-bg-warning" title="Hojas sin responder">1</span>')
        self.assertContains(respuesta, "1 hoja sin responder.")

    def test_el_admin_supervisa_y_responde_las_de_nexalys(self):
        admin = User.objects.create_superuser("jefe", "j@ejemplo.com", CLAVE)
        self.client.force_login(admin)
        lista = self.client.get(reverse("reclamos:consola_lista"))
        self.assertContains(lista, self.de_tienda.codigo)
        self.assertContains(lista, '<span class="consola__globo" title="Hojas sin responder">2</span>')
        resumen = self.client.get(reverse("panel_admin"))
        self.assertContains(resumen, f"Hoja N.° {self.de_nexalys.codigo}")
        # La de la tienda no la puede responder el admin.
        url_tienda = reverse("reclamos:consola_detalle", args=[self.de_tienda.pk])
        self.assertContains(self.client.get(url_tienda), "Esta hoja la responde la tienda")
        self.assertEqual(self.client.post(url_tienda, {"respuesta": "Respuesta del administrador."}).status_code, 403)
        url = reverse("reclamos:consola_detalle", args=[self.de_nexalys.pk])
        self.client.post(url, {"respuesta": "Revisamos tu caso y corregimos el error de la página."})
        self.de_nexalys.refresh_from_db()
        self.assertEqual(self.de_nexalys.estado, Reclamo.Estado.RESPONDIDO)
        self.assertTrue(AccionAdmin.objects.filter(tipo=AccionAdmin.Tipo.RESPONDER_RECLAMO).exists())

    def test_si_la_tienda_se_elimina_la_hoja_queda_y_la_responde_el_admin(self):
        self.tienda.usuario.delete()  # borra la cuenta y su tienda
        self.de_tienda.refresh_from_db()
        self.assertIsNone(self.de_tienda.tienda)
        self.assertEqual(self.de_tienda.proveedor_nombre, "Tienda Uno")
        admin = User.objects.create_superuser("jefe", "j@ejemplo.com", CLAVE)
        self.client.force_login(admin)
        self.client.post(reverse("reclamos:consola_detalle", args=[self.de_tienda.pk]), {"respuesta": "La tienda cerró; te ayudamos nosotros."})
        self.de_tienda.refresh_from_db()
        self.assertEqual(self.de_tienda.estado, Reclamo.Estado.RESPONDIDO)

    def test_clientes_y_otras_tiendas_no_entran(self):
        cliente = User.objects.create_user("cli", "c@ejemplo.com", CLAVE)
        cliente.groups.add(Group.objects.get(name="Cliente"))
        self.client.force_login(cliente)
        self.assertEqual(self.client.get(reverse("reclamos:consola_lista")).status_code, 403)
        self.assertEqual(self.client.get(reverse("reclamos:tienda_lista")).status_code, 403)
        self.assertEqual(self.client.get(reverse("reclamos:hoja", args=[self.de_tienda.pk])).status_code, 403)
        otra = crear_tienda("t2", "Tienda Dos", "922222222")
        self.client.force_login(otra.usuario)
        self.assertEqual(self.client.get(reverse("reclamos:tienda_detalle", args=[self.de_tienda.pk])).status_code, 404)
