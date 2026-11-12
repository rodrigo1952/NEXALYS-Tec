"""Privacidad (Ley 29733): casilla de consentimiento con prueba, aceptar al entrar, descargar mis datos y derechos."""
import json
from datetime import date
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from administracion.models import AccionAdmin
from catalogo.models import Categoria, Marca, Producto
from favoritos.models import Favorito
from tiendas.tests import DATOS_VALIDOS, crear_tienda

from . import privacidad
from .models import ConsentimientoPrivacidad, SolicitudDerecho

CLAVE = "ClaveSegura#2026"
REGISTRO = {
    "username": "ana", "first_name": "Ana", "last_name": "Quispe", "email": "ana@ejemplo.com",
    "password1": CLAVE, "password2": CLAVE,
}
DATOS_TITULAR = dict(
    PRIVACIDAD_TITULAR="Fernando Rodrigo Diaz Ayala", PRIVACIDAD_DOCUMENTO="DNI 00000000",
    PRIVACIDAD_DIRECCION="Jr. Prueba 123, Quillabamba", PRIVACIDAD_CORREO="datos@ejemplo.com",
    PRIVACIDAD_BANCO_DATOS="Usuarios de NEXALYS Tec (código 00000)", PRIVACIDAD_SERVIDOR="PythonAnywhere (Estados Unidos)",
)


def crear_cliente(usuario="cliente1"):
    user = User.objects.create_user(usuario, f"{usuario}@ejemplo.com", CLAVE, first_name="Ana", last_name="Quispe")
    user.groups.add(Group.objects.get(name="Cliente"))
    return user


class CasillaAlRegistrarseTests(TestCase):
    def test_la_casilla_empieza_sin_marcar_y_enlaza_la_politica(self):
        respuesta = self.client.get(reverse("registro"))
        self.assertContains(respuesta, 'name="acepto_privacidad"')
        self.assertNotContains(respuesta, 'name="acepto_privacidad" checked')
        self.assertContains(respuesta, f'acepto la <a href="{reverse("privacidad")}" target="_blank" rel="noopener">política de privacidad</a>')

    def test_sin_aceptar_no_se_crea_la_cuenta(self):
        respuesta = self.client.post(reverse("registro"), REGISTRO)
        self.assertContains(respuesta, "Para crear la cuenta debes aceptar la política de privacidad.")
        self.assertFalse(User.objects.filter(username="ana").exists())

    def test_cliente_queda_con_prueba_del_consentimiento(self):
        self.client.post(reverse("registro"), {**REGISTRO, "acepto_privacidad": "on"}, REMOTE_ADDR="10.1.1.1")
        consentimiento = ConsentimientoPrivacidad.objects.get(usuario__username="ana")
        self.assertEqual(consentimiento.version, privacidad.VERSION_POLITICA)
        self.assertEqual(consentimiento.origen, ConsentimientoPrivacidad.Origen.REGISTRO_CLIENTE)
        self.assertEqual(consentimiento.ip, "10.1.1.1")

    def test_tienda_queda_con_prueba_del_consentimiento(self):
        sin_casilla = {k: v for k, v in DATOS_VALIDOS.items() if k != "acepto_privacidad"}
        self.client.post(reverse("tiendas:registro"), sin_casilla)
        self.assertFalse(User.objects.filter(username=DATOS_VALIDOS["username"]).exists())
        self.client.post(reverse("tiendas:registro"), DATOS_VALIDOS)
        consentimiento = ConsentimientoPrivacidad.objects.get(usuario__username=DATOS_VALIDOS["username"])
        self.assertEqual(consentimiento.origen, ConsentimientoPrivacidad.Origen.REGISTRO_TIENDA)


@override_settings(PRIVACIDAD_OBLIGATORIA=True)
class AceptarAlEntrarTests(TestCase):
    def setUp(self):
        self.cliente = crear_cliente()
        self.client.force_login(self.cliente)

    def test_cuenta_anterior_debe_aceptar_para_seguir(self):
        respuesta = self.client.get(reverse("favoritos:lista"))
        self.assertRedirects(respuesta, f"{reverse('privacidad_aceptar')}?next={reverse('favoritos:lista')}")
        pagina = self.client.get(respuesta["Location"])
        self.assertContains(pagina, "Acepta nuestra política de privacidad")
        self.assertContains(pagina, "Eliminar mi cuenta")

    def test_sin_marcar_la_casilla_no_avanza(self):
        respuesta = self.client.post(reverse("privacidad_aceptar"), {"next": "/favoritos/"})
        self.assertContains(respuesta, "Marca la casilla para aceptar la política y seguir.")
        self.assertFalse(ConsentimientoPrivacidad.objects.exists())

    def test_al_aceptar_vuelve_a_donde_iba(self):
        respuesta = self.client.post(reverse("privacidad_aceptar"), {"acepto": "on", "next": "/favoritos/"})
        self.assertRedirects(respuesta, "/favoritos/", fetch_redirect_response=False)
        self.assertEqual(ConsentimientoPrivacidad.objects.get().origen, ConsentimientoPrivacidad.Origen.AL_ENTRAR)
        self.assertEqual(self.client.get("/favoritos/").status_code, 200)

    def test_no_redirige_a_otro_sitio(self):
        respuesta = self.client.post(reverse("privacidad_aceptar"), {"acepto": "on", "next": "https://malo.example/"})
        self.assertRedirects(respuesta, reverse("inicio"), fetch_redirect_response=False)

    def test_sin_aceptar_puede_leer_descargar_pedir_borrar_o_salir(self):
        for nombre in ("privacidad", "privacidad_solicitud", "mis_datos", "eliminar_cuenta"):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("inicio"), fetch_redirect_response=False)

    def test_si_cambia_la_politica_se_pide_de_nuevo(self):
        ConsentimientoPrivacidad.objects.create(
            usuario=self.cliente, version="2020-01-01", origen="registro_cliente", fecha="2020-01-01T00:00:00Z"
        )
        respuesta = self.client.get(reverse("privacidad_aceptar"))
        self.assertContains(respuesta, "Actualizamos nuestra política de privacidad")
        self.client.post(reverse("privacidad_aceptar"), {"acepto": "on"})
        versiones = set(ConsentimientoPrivacidad.objects.values_list("version", flat=True))
        self.assertEqual(versiones, {"2020-01-01", privacidad.VERSION_POLITICA})  # queda el historial

    def test_con_la_version_vigente_no_se_pide(self):
        ConsentimientoPrivacidad.objects.create(
            usuario=self.cliente, version=privacidad.VERSION_POLITICA, origen="registro_cliente", fecha="2026-11-11T00:00:00Z"
        )
        self.assertEqual(self.client.get(reverse("favoritos:lista")).status_code, 200)

    def test_el_administrador_no_la_acepta(self):
        admin = User.objects.create_superuser("jefe", "j@ejemplo.com", CLAVE)
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("panel_admin")).status_code, 200)

    def test_visitantes_sin_cuenta_no_ven_nada(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("inicio")).status_code, 200)


class DescargarMisDatosTests(TestCase):
    def test_cliente_descarga_sus_datos_sin_la_contrasena(self):
        cliente = crear_cliente()
        tienda = crear_tienda()
        producto = Producto.objects.create(
            tienda=tienda, categoria=Categoria.objects.get(nombre="Celulares"), marca=Marca.objects.get(nombre="Samsung"),
            nombre="Galaxy A15", precio=Decimal("700.00"), stock=5,
        )
        Favorito.objects.create(usuario=cliente, producto=producto, precio_guardado=700, precio_visto=700)
        self.client.force_login(cliente)
        respuesta = self.client.get(reverse("mis_datos"))
        self.assertEqual(respuesta["Content-Disposition"], 'attachment; filename="mis-datos-nexalys-cliente1.json"')
        datos = json.loads(respuesta.content)
        self.assertEqual(datos["cuenta"]["correo"], "cliente1@ejemplo.com")
        self.assertEqual(datos["cuenta"]["rol"], ["Cliente"])
        self.assertEqual(datos["favoritos"][0]["producto"], "Galaxy A15")
        self.assertNotIn("password", respuesta.content.decode())
        self.assertNotIn(cliente.password, respuesta.content.decode())

    def test_tienda_descarga_tambien_su_tienda(self):
        tienda = crear_tienda()
        self.client.force_login(tienda.usuario)
        datos = json.loads(self.client.get(reverse("mis_datos")).content)
        self.assertEqual(datos["tienda"]["nombre"], "Tienda Uno")
        self.assertEqual(datos["tienda"]["whatsapp"], "911111111")

    def test_requiere_iniciar_sesion(self):
        self.assertEqual(self.client.get(reverse("mis_datos")).status_code, 302)

    def test_acceso_desde_mi_perfil(self):
        self.client.force_login(crear_cliente())
        respuesta = self.client.get(reverse("mi_cuenta"))
        self.assertContains(respuesta, f'href="{reverse("mis_datos")}"')
        self.assertContains(respuesta, f'href="{reverse("privacidad_solicitud")}"')


class SolicitudDeDerechosTests(TestCase):
    datos = {"nombre": "Luis Mamani", "correo": "luis@ejemplo.com", "tipo": "cancelacion", "detalle": "Borren mis datos de la venta 12."}

    def test_dias_habiles_sin_sabado_ni_domingo(self):
        viernes = date(2026, 11, 13)
        self.assertEqual(privacidad.sumar_dias_habiles(viernes, 1), date(2026, 11, 16))
        self.assertEqual(privacidad.sumar_dias_habiles(viernes, 10), date(2026, 11, 27))

    def test_visitante_sin_cuenta_envia_y_recibe_constancia(self):
        with mock.patch("django.utils.timezone.localdate", return_value=date(2026, 11, 13)):
            respuesta = self.client.post(reverse("privacidad_solicitud"), self.datos)
        solicitud = SolicitudDerecho.objects.get()
        self.assertIsNone(solicitud.usuario)
        self.assertEqual(solicitud.vence, date(2026, 11, 27))  # 10 días hábiles
        self.assertContains(respuesta, "a más tardar el <strong>27/11/2026</strong>")
        self.assertEqual(mail.outbox[0].to, ["luis@ejemplo.com"])
        self.assertIn("27/11/2026", mail.outbox[0].body)

    def test_plazo_segun_lo_que_pide(self):
        with mock.patch("django.utils.timezone.localdate", return_value=date(2026, 11, 13)):
            self.client.post(reverse("privacidad_solicitud"), {**self.datos, "tipo": "acceso"})
        self.assertEqual(SolicitudDerecho.objects.get().vence, date(2026, 12, 11))  # 20 días hábiles

    def test_con_cuenta_queda_vinculada_y_con_sus_datos(self):
        cliente = crear_cliente()
        self.client.force_login(cliente)
        respuesta = self.client.get(reverse("privacidad_solicitud"))
        self.assertContains(respuesta, 'value="cliente1@ejemplo.com"')
        self.client.post(reverse("privacidad_solicitud"), self.datos)
        self.assertEqual(SolicitudDerecho.objects.get().usuario, cliente)

    def test_maximo_3_por_hora(self):
        for _ in range(3):
            self.client.post(reverse("privacidad_solicitud"), self.datos)
        respuesta = self.client.post(reverse("privacidad_solicitud"), self.datos)
        self.assertContains(respuesta, "Demasiados intentos.")
        self.assertEqual(SolicitudDerecho.objects.count(), 3)


class PoliticaTests(TestCase):
    def test_sin_datos_del_responsable_dice_por_completar(self):
        with override_settings(**{nombre: "" for nombre in DATOS_TITULAR}):
            respuesta = self.client.get(reverse("privacidad"))
        self.assertContains(respuesta, '<span class="dato-pendiente">por completar</span>', count=6)

    @override_settings(**DATOS_TITULAR)
    def test_con_los_datos_del_env(self):
        respuesta = self.client.get(reverse("privacidad"))
        for valor in DATOS_TITULAR.values():
            self.assertContains(respuesta, valor)
        self.assertNotContains(respuesta, "dato-pendiente")

    def test_tiene_todo_lo_que_pide_la_ley(self):
        respuesta = self.client.get(reverse("privacidad"))
        for ancla in ("responsable", "datos", "obligatorios", "compartir", "plazos", "derechos", "cookies", "seguridad", "reglas"):
            self.assertContains(respuesta, f'id="{ancla}"')
        for texto in ("máximo 8 días hábiles", "máximo 20 días hábiles", "máximo 10 días hábiles",
                      "Autoridad Nacional de Protección de Datos Personales", "flujo transfronterizo",
                      f"Versión vigente: {privacidad.VERSION_POLITICA}", "No usamos cookies de publicidad"):
            self.assertContains(respuesta, texto)


class ConsolaPrivacidadTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("jefe", "jefe@ejemplo.com", CLAVE)
        self.client.force_login(self.admin)
        self.solicitud = SolicitudDerecho.objects.create(
            nombre="Luis Mamani", correo="luis@ejemplo.com", tipo="rectificacion",
            detalle="Mi apellido es Mamani, no Mamami.", vence=date(2030, 1, 10),
        )

    def test_lista_globo_y_tarea_pendiente(self):
        respuesta = self.client.get(reverse("administracion:solicitudes"))
        self.assertContains(respuesta, "Luis Mamani")
        self.assertContains(respuesta, '<span class="consola__globo" title="Solicitudes sin responder">1</span>')
        resumen = self.client.get(reverse("panel_admin"))
        self.assertContains(resumen, "Rectificación · Luis Mamani")
        self.assertContains(resumen, "responder hasta el 10/01/2030")

    def test_responder_envia_correo_y_queda_en_el_historial(self):
        url = reverse("administracion:solicitud_detalle", args=[self.solicitud.pk])
        respuesta = self.client.post(url, {"respuesta": "Corregimos tu apellido en la venta."}, follow=True)
        self.assertContains(respuesta, "Respuesta guardada y enviada a luis@ejemplo.com.")
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, SolicitudDerecho.Estado.ATENDIDA)
        self.assertEqual(self.solicitud.atendida_por, "jefe")
        self.assertEqual(mail.outbox[-1].to, ["luis@ejemplo.com"])
        self.assertIn("Corregimos tu apellido", mail.outbox[-1].body)
        self.assertTrue(AccionAdmin.objects.filter(tipo=AccionAdmin.Tipo.RESPONDER_SOLICITUD).exists())
        # Una vez respondida, no se responde dos veces.
        self.client.post(url, {"respuesta": "Otra respuesta distinta."})
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.respuesta, "Corregimos tu apellido en la venta.")

    def test_aviso_si_faltan_datos_del_responsable(self):
        with override_settings(PRIVACIDAD_TITULAR="", PRIVACIDAD_CORREO=""):
            self.assertContains(self.client.get(reverse("panel_admin")), "Completa los datos de privacidad")
            self.assertContains(self.client.get(reverse("administracion:solicitudes")), "Faltan datos en la política de privacidad.")
        with override_settings(**DATOS_TITULAR):
            self.assertNotContains(self.client.get(reverse("panel_admin")), "Completa los datos de privacidad")

    def test_solo_el_administrador(self):
        self.client.force_login(crear_cliente())
        self.assertEqual(self.client.get(reverse("administracion:solicitudes")).status_code, 403)
        url = reverse("administracion:solicitud_detalle", args=[self.solicitud.pk])
        self.assertEqual(self.client.post(url, {"respuesta": "Hola, ya está."}).status_code, 403)
