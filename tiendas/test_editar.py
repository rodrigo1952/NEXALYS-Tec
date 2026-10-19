"""Pruebas: la tienda edita sus datos, su logo y su horario de atención."""

import io
import shutil
import tempfile
from datetime import datetime, time

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import HorarioDia, Tienda, a_las, hora_12
from .tests import crear_tienda

CARPETA_MEDIA = tempfile.mkdtemp()


def h(campo, valor):
    """h("abre_0", "13:00") -> {"horario-abre_0_0": "1:00", "horario-abre_0_1": "pm"}"""
    horas, minutos = (int(parte) for parte in valor.split(":"))
    return {
        f"horario-{campo}_0": f"{horas % 12 or 12}:{minutos:02d}",
        f"horario-{campo}_1": "am" if horas < 12 else "pm",
    }


def horario(**campos):
    datos = {}
    for campo, valor in campos.items():
        datos.update(h(campo, valor))
    return datos


def imagen(nombre="logo.png", ancho=1000, alto=1000):
    archivo = io.BytesIO()
    Image.new("RGB", (ancho, alto), "red").save(archivo, "PNG")
    return SimpleUploadedFile(nombre, archivo.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=CARPETA_MEDIA)
class EditarTiendaTests(TestCase):
    url = reverse("tiendas:editar")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.tienda = crear_tienda()
        self.client.force_login(self.tienda.usuario)

    def datos(self, **cambios):
        datos = {
            "datos-nombre": "Tienda Uno",
            "datos-direccion": "Jr. Lima 100",
            "datos-whatsapp": "911111111",
            "datos-descripcion": "",
        }
        datos.update(cambios)
        return datos

    def test_editar_datos(self):
        respuesta = self.client.post(self.url, self.datos(**{
            "datos-nombre": "Tienda Uno Renovada",
            "datos-direccion": "Av. Nueva   200",
            "datos-whatsapp": "+51 933 333 333",
        }))
        self.assertRedirects(respuesta, reverse("tiendas:panel"))
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.nombre, "Tienda Uno Renovada")
        self.assertEqual(self.tienda.direccion, "Av. Nueva 200")
        self.assertEqual(self.tienda.whatsapp, "933333333")

    def test_nombre_de_otra_tienda_se_rechaza(self):
        crear_tienda("tienda2", "Tienda Dos", "922222222")
        respuesta = self.client.post(self.url, self.datos(**{"datos-nombre": "tienda dos"}))
        self.assertIn("nombre", respuesta.context["form"].errors)

    def test_whatsapp_de_otra_tienda_se_rechaza(self):
        crear_tienda("tienda2", "Tienda Dos", "922222222")
        respuesta = self.client.post(self.url, self.datos(**{"datos-whatsapp": "922222222"}))
        self.assertIn("whatsapp", respuesta.context["form"].errors)

    def test_cliente_no_puede_entrar(self):
        cliente = User.objects.create_user("cliente1", "c@ejemplo.com", "ClaveSegura#2026")
        cliente.groups.add(Group.objects.get(name="Cliente"))
        self.client.force_login(cliente)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_panel_tiene_el_enlace_para_editar(self):
        self.assertContains(self.client.get(reverse("tiendas:panel")), self.url)

    def test_logo_se_optimiza(self):
        self.client.post(self.url, self.datos(**{"datos-logo": imagen(ancho=1600, alto=900)}))
        self.tienda.refresh_from_db()
        self.assertTrue(self.tienda.logo.name.endswith(".webp"))
        with Image.open(self.tienda.logo.path) as guardada:
            self.assertLessEqual(max(guardada.size), 400)

    # --- Horario ----------------------------------------------------------------
    def test_guardar_horario(self):
        respuesta = self.client.post(self.url, self.datos(**horario(abre_0="09:00", cierra_0="18:00", abre_5="10:00", cierra_5="13:00")))
        self.assertRedirects(respuesta, reverse("tiendas:panel"))
        semana = dict(self.tienda.horario_semana())
        self.assertEqual(semana["Lunes"], "9:00 a. m. – 6:00 p. m.")
        self.assertEqual(semana["Sábado"], "10:00 a. m. – 1:00 p. m.")
        self.assertEqual(semana["Domingo"], "Cerrado")

    def test_horario_incompleto_se_rechaza(self):
        respuesta = self.client.post(self.url, self.datos(**horario(abre_0="09:00")))
        self.assertIn("cierra_0", respuesta.context["horario"].errors)
        self.assertFalse(HorarioDia.objects.exists())

    def test_cierre_antes_de_apertura_se_rechaza(self):
        respuesta = self.client.post(self.url, self.datos(**horario(abre_0="18:00", cierra_0="09:00")))
        self.assertIn("cierra_0", respuesta.context["horario"].errors)

    def test_guardar_horario_con_refrigerio(self):
        respuesta = self.client.post(self.url, self.datos(**horario(abre_0="08:00", descanso_inicio_0="13:00", descanso_fin_0="15:00", cierra_0="22:00")))
        self.assertRedirects(respuesta, reverse("tiendas:panel"))
        semana = dict(self.tienda.horario_semana())
        self.assertEqual(semana["Lunes"], "8:00 a. m. – 1:00 p. m. y 3:00 p. m. – 10:00 p. m.")

    def test_refrigerio_incompleto_se_rechaza(self):
        respuesta = self.client.post(self.url, self.datos(**horario(abre_0="08:00", descanso_inicio_0="13:00", cierra_0="22:00")))
        self.assertIn("descanso_fin_0", respuesta.context["horario"].errors)

    def test_refrigerio_fuera_del_horario_se_rechaza(self):
        respuesta = self.client.post(self.url, self.datos(**horario(abre_0="08:00", descanso_inicio_0="12:00", descanso_fin_0="23:00", cierra_0="22:00")))
        self.assertIn("descanso_inicio_0", respuesta.context["horario"].errors)

    def test_refrigerio_sin_horario_se_rechaza(self):
        respuesta = self.client.post(self.url, self.datos(**horario(descanso_inicio_0="13:00", descanso_fin_0="15:00")))
        self.assertIn("descanso_inicio_0", respuesta.context["horario"].errors)

    def test_error_en_horario_no_guarda_los_datos(self):
        self.client.post(self.url, self.datos(**{"datos-nombre": "Otro nombre"}, **horario(abre_0="09:00")))
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.nombre, "Tienda Uno")


class EstadoAtencionTests(TestCase):
    """El lunes 19/10/2026 es lunes; las horas son de Perú (America/Lima)."""

    def setUp(self):
        self.tienda = crear_tienda()
        HorarioDia.objects.create(tienda=self.tienda, dia=HorarioDia.Dia.LUNES, abre=time(9), cierra=time(18))
        HorarioDia.objects.create(tienda=self.tienda, dia=HorarioDia.Dia.MARTES, abre=time(9), cierra=time(18))

    def a_las(self, dia, hora, minuto=0):
        return timezone.make_aware(datetime(2026, 10, dia, hora, minuto))

    def test_abierto(self):
        estado = self.tienda.estado_atencion(self.a_las(19, 10))
        self.assertTrue(estado["abierto"])
        self.assertIn("cierra a las 6:00 p. m.", estado["texto"])

    def test_antes_de_abrir(self):
        estado = self.tienda.estado_atencion(self.a_las(19, 8))
        self.assertFalse(estado["abierto"])
        self.assertIn("abre hoy a las 9:00 a. m.", estado["texto"])

    def test_despues_de_cerrar_abre_manana(self):
        estado = self.tienda.estado_atencion(self.a_las(19, 18, 30))
        self.assertFalse(estado["abierto"])
        self.assertIn("abre mañana a las 9:00 a. m.", estado["texto"])

    def test_martes_en_la_noche_abre_el_lunes(self):
        estado = self.tienda.estado_atencion(self.a_las(20, 20))
        self.assertIn("abre el lunes a las 9:00 a. m.", estado["texto"])

    def test_sin_horario_no_muestra_estado(self):
        otra = crear_tienda("tienda2", "Tienda Dos", "922222222")
        self.assertIsNone(otra.estado_atencion())

    def test_perfil_publico_muestra_el_horario(self):
        respuesta = self.client.get(reverse("tiendas:perfil", args=[self.tienda.pk]))
        self.assertContains(respuesta, "Horario de atención")
        self.assertContains(respuesta, "9:00 a. m. – 6:00 p. m.")


class RefrigerioTests(TestCase):
    """Lunes 19/10/2026: abre 8:00 a. m., refrigerio de 1:00 a 3:00 p. m., cierra 10:00 p. m."""

    def setUp(self):
        self.tienda = crear_tienda()
        HorarioDia.objects.create(
            tienda=self.tienda, dia=HorarioDia.Dia.LUNES,
            abre=time(8), descanso_inicio=time(13), descanso_fin=time(15), cierra=time(22),
        )

    def estado(self, hora, minuto=0):
        return self.tienda.estado_atencion(timezone.make_aware(datetime(2026, 10, 19, hora, minuto)))

    def test_en_la_manana_avisa_el_refrigerio(self):
        estado = self.estado(11)
        self.assertTrue(estado["abierto"])
        self.assertIn("cierra por refrigerio a la 1:00 p. m.", estado["texto"])

    def test_durante_el_refrigerio(self):
        estado = self.estado(14)
        self.assertFalse(estado["abierto"])
        self.assertIn("Cerrado por refrigerio · vuelve a abrir a las 3:00 p. m.", estado["texto"])

    def test_en_la_tarde(self):
        estado = self.estado(16, 30)
        self.assertTrue(estado["abierto"])
        self.assertIn("cierra a las 10:00 p. m.", estado["texto"])

    def test_a_la_una_en_punto_ya_esta_en_refrigerio(self):
        self.assertFalse(self.estado(13)["abierto"])


class Formato12HorasTests(SimpleTestCase):
    def test_horas(self):
        self.assertEqual(hora_12(time(0, 5)), "12:05 a. m.")
        self.assertEqual(hora_12(time(9)), "9:00 a. m.")
        self.assertEqual(hora_12(time(12)), "12:00 p. m.")
        self.assertEqual(hora_12(time(13, 30)), "1:30 p. m.")

    def test_a_la_una(self):
        self.assertEqual(a_las(time(13)), "a la 1:00 p. m.")
        self.assertEqual(a_las(time(15)), "a las 3:00 p. m.")


class BotonVerTiendaTests(TestCase):
    def test_detalle_tiene_boton_ver_tienda(self):
        from catalogo.models import Categoria, Marca, Producto
        tienda = crear_tienda()
        producto = Producto.objects.create(
            tienda=tienda, categoria=Categoria.objects.get(nombre="Celulares"),
            marca=Marca.objects.get(nombre="Samsung"), nombre="Galaxy A15", precio="700.00", stock=3,
        )
        respuesta = self.client.get(reverse("catalogo:detalle", args=[producto.pk]))
        self.assertContains(respuesta, "Ver tienda")
        self.assertContains(respuesta, reverse("tiendas:perfil", args=[tienda.pk]))


class HorarioEnListasTests(TestCase):
    """Las horas se eligen en listas con a. m. / p. m., sin depender del navegador."""

    def setUp(self):
        self.tienda = crear_tienda()
        self.client.force_login(self.tienda.usuario)

    def test_las_listas_tienen_hora_y_am_pm(self):
        respuesta = self.client.get(reverse("tiendas:editar"))
        self.assertContains(respuesta, '<option value="9:30">9:30</option>', html=True)
        self.assertContains(respuesta, '<option value="pm">p. m.</option>', html=True)

    def test_hora_sin_am_pm_se_rechaza(self):
        respuesta = self.client.post(reverse("tiendas:editar"), {
            "datos-nombre": "Tienda Uno", "datos-direccion": "Jr. Lima 100", "datos-whatsapp": "911111111",
            "horario-abre_0_0": "9:00", "horario-abre_0_1": "",
            **horario(cierra_0="18:00"),
        })
        self.assertIn("abre_0", respuesta.context["horario"].errors)
        self.assertFalse(HorarioDia.objects.exists())

    def test_doce_del_mediodia_y_medianoche(self):
        from .forms import HoraAmPmField
        campo = HoraAmPmField()
        self.assertEqual(campo.clean(["12:00", "pm"]), time(12))
        self.assertEqual(campo.clean(["12:30", "am"]), time(0, 30))
        self.assertEqual(campo.clean(["9:00", "pm"]), time(21))
        self.assertIsNone(campo.clean(["", ""]))

    def test_la_hora_guardada_aparece_seleccionada(self):
        HorarioDia.objects.create(tienda=self.tienda, dia=HorarioDia.Dia.LUNES, abre=time(8), cierra=time(22))
        respuesta = self.client.get(reverse("tiendas:editar"))
        # Cierra a las 22:00 -> se ve "10:00" + "p. m."; abre 8:00 -> "8:00" + "a. m."
        self.assertContains(respuesta, '<option value="10:00" selected>10:00</option>', html=True)
        self.assertContains(respuesta, '<option value="8:00" selected>8:00</option>', html=True)
        self.assertContains(respuesta, '<option value="pm" selected>p. m.</option>', html=True)
        self.assertContains(respuesta, '<option value="am" selected>a. m.</option>', html=True)


class AmpliarImagenesTests(TestCase):
    def test_logo_del_perfil_se_puede_ampliar(self):
        tienda = crear_tienda()
        tienda.logo = "tiendas/logos/logo.webp"  # solo se revisa el HTML, no hace falta el archivo
        tienda.save(update_fields=["logo"])
        respuesta = self.client.get(reverse("tiendas:perfil", args=[tienda.pk]))
        self.assertContains(respuesta, 'data-ampliar="/media/tiendas/logos/logo.webp"')
        self.assertContains(respuesta, 'id="modal-imagen"')
