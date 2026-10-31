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


def grupos(*lista, borrar=()):
    """
    Datos del horario por grupos. Cada grupo: (días, abre, cierra) o (días, abre, cierra, desde, hasta).
    grupos(([0, 1, 2], "9:00 a. m.", "6:00 p. m.")) -> lunes a miércoles de 9 a 6.
    """
    datos = {"horario-TOTAL_FORMS": str(len(lista)), "horario-INITIAL_FORMS": "0",
             "horario-MIN_NUM_FORMS": "0", "horario-MAX_NUM_FORMS": "7"}
    for n, grupo in enumerate(lista):
        dias, abre, cierra, *refrigerio = grupo
        datos[f"horario-{n}-dias"] = [str(d) for d in dias]
        datos[f"horario-{n}-abre"] = abre
        datos[f"horario-{n}-cierra"] = cierra
        if refrigerio:
            datos[f"horario-{n}-con_refrigerio"] = "on"
            datos[f"horario-{n}-descanso_inicio"], datos[f"horario-{n}-descanso_fin"] = refrigerio
        if n in borrar:
            datos[f"horario-{n}-DELETE"] = "on"
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
            "datos-clave_actual": "ClaveSegura#2026",  # se pide al cambiar nombre, dirección o WhatsApp
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

    # --- Horario por grupos de días ----------------------------------------------
    def errores(self, respuesta):
        formset = respuesta.context["horario"]
        return [e for form in formset.forms for lista in form.errors.values() for e in lista] + list(formset.non_form_errors())

    def test_guardar_horario_por_grupos(self):
        respuesta = self.client.post(self.url, self.datos(**grupos(
            ([0, 1, 2, 3, 4], "9:00 a. m.", "6:00 p. m."),
            ([5], "10:00 a. m.", "1:00 p. m."),
        )))
        self.assertRedirects(respuesta, reverse("tiendas:panel"))
        semana = dict(self.tienda.horario_semana())
        self.assertEqual(semana["Lunes"], "9:00 a. m. – 6:00 p. m.")
        self.assertEqual(semana["Viernes"], "9:00 a. m. – 6:00 p. m.")
        self.assertEqual(semana["Sábado"], "10:00 a. m. – 1:00 p. m.")
        self.assertEqual(semana["Domingo"], "Cerrado")  # sin marcar = cerrado

    def test_la_hora_se_puede_escribir_como_sea(self):
        self.client.post(self.url, self.datos(**grupos(([0], "8.30 am", "20:30"))))
        self.assertEqual(dict(self.tienda.horario_semana())["Lunes"], "8:30 a. m. – 8:30 p. m.")

    def test_hora_sin_am_pm_se_rechaza(self):
        respuesta = self.client.post(self.url, self.datos(**grupos(([0], "8:30", "6:00 p. m."))))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("¿8:30 de la mañana o de la noche? Agrega a. m. o p. m.", self.errores(respuesta))
        self.assertFalse(HorarioDia.objects.exists())

    def test_horario_incompleto_se_rechaza(self):
        respuesta = self.client.post(self.url, self.datos(**grupos(([0], "9:00 a. m.", ""))))
        self.assertIn("Escribe a qué hora cierras.", self.errores(respuesta))
        self.assertFalse(HorarioDia.objects.exists())

    def test_horas_sin_dias_se_rechaza(self):
        respuesta = self.client.post(self.url, self.datos(**grupos(([], "9:00 a. m.", "6:00 p. m."))))
        self.assertIn("Marca los días en que usas este horario.", self.errores(respuesta))

    def test_dias_sin_horas_quedan_cerrados(self):
        # El grupo inicial (lunes a sábado sin horas) no impide guardar los datos de la tienda.
        respuesta = self.client.post(self.url, self.datos(**grupos(([0, 1, 2, 3, 4, 5], "", ""))))
        self.assertRedirects(respuesta, reverse("tiendas:panel"))
        self.assertFalse(self.tienda.tiene_horario())

    def test_un_dia_en_dos_grupos_se_rechaza(self):
        respuesta = self.client.post(self.url, self.datos(**grupos(
            ([0, 1], "9:00 a. m.", "6:00 p. m."), ([1], "10:00 a. m.", "1:00 p. m."))))
        self.assertIn("El martes está marcado en el horario 1 y en el 2. Déjalo marcado solo en uno.", self.errores(respuesta))

    def test_grupo_quitado_no_cuenta(self):
        self.client.post(self.url, self.datos(**grupos(
            ([0], "9:00 a. m.", "6:00 p. m."), ([0], "10:00 a. m.", "1:00 p. m."), borrar=(1,))))
        self.assertEqual(dict(self.tienda.horario_semana())["Lunes"], "9:00 a. m. – 6:00 p. m.")

    def test_cierre_antes_de_apertura_se_rechaza(self):
        respuesta = self.client.post(self.url, self.datos(**grupos(([0], "6:00 p. m.", "9:00 a. m."))))
        self.assertIn("La hora de cierre debe ser después de la de apertura.", self.errores(respuesta))

    def test_guardar_horario_con_refrigerio(self):
        respuesta = self.client.post(self.url, self.datos(**grupos(
            ([0], "8:00 a. m.", "10:00 p. m.", "1:00 p. m.", "3:00 p. m."))))
        self.assertRedirects(respuesta, reverse("tiendas:panel"))
        self.assertEqual(dict(self.tienda.horario_semana())["Lunes"], "8:00 a. m. – 1:00 p. m. y 3:00 p. m. – 10:00 p. m.")

    def test_refrigerio_incompleto_se_rechaza(self):
        respuesta = self.client.post(self.url, self.datos(**grupos(([0], "8:00 a. m.", "10:00 p. m.", "1:00 p. m.", ""))))
        self.assertIn("Escribe desde y hasta qué hora es el refrigerio (o desmarca la casilla).", self.errores(respuesta))

    def test_refrigerio_fuera_del_horario_se_rechaza(self):
        respuesta = self.client.post(self.url, self.datos(**grupos(([0], "8:00 a. m.", "10:00 p. m.", "12:00 p. m.", "11:00 p. m."))))
        self.assertIn("El refrigerio debe estar dentro del horario: después de abrir y antes de cerrar.", self.errores(respuesta))

    def test_refrigerio_desmarcado_no_se_guarda(self):
        datos = self.datos(**grupos(([0], "8:00 a. m.", "10:00 p. m.")))
        datos.update({"horario-0-descanso_inicio": "1:00 p. m.", "horario-0-descanso_fin": "3:00 p. m."})
        self.client.post(self.url, datos)
        self.assertEqual(dict(self.tienda.horario_semana())["Lunes"], "8:00 a. m. – 10:00 p. m.")

    def test_error_en_horario_no_guarda_los_datos(self):
        self.client.post(self.url, self.datos(**{"datos-nombre": "Otro nombre"}, **grupos(([0], "9:00 a. m.", ""))))
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.nombre, "Tienda Uno")

    def test_al_editar_los_dias_iguales_salen_juntos(self):
        for dia in range(6):
            HorarioDia.objects.create(tienda=self.tienda, dia=dia, abre=time(8), cierra=time(21))
        HorarioDia.objects.create(tienda=self.tienda, dia=6, abre=time(9), cierra=time(13))
        respuesta = self.client.get(self.url)
        formset = respuesta.context["horario"]
        self.assertEqual(len(formset.forms), 2)
        self.assertEqual(formset.forms[0].initial["dias"], [0, 1, 2, 3, 4, 5])
        self.assertContains(respuesta, 'value="8:00 a. m."')
        self.assertContains(respuesta, 'id="horas-sugeridas"')
        self.assertContains(respuesta, '<option value="8:00 a. m."></option>', html=True)
        self.assertContains(respuesta, 'id="plantilla-grupo"')
        self.assertContains(respuesta, "js/horario.js")


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
        self.assertEqual(estado["detalle"], "Cierra a las 6:00 p. m.")

    def test_antes_de_abrir(self):
        estado = self.tienda.estado_atencion(self.a_las(19, 8))
        self.assertFalse(estado["abierto"])
        self.assertEqual(estado["detalle"], "Abre hoy a las 9:00 a. m.")

    def test_despues_de_cerrar_abre_manana(self):
        estado = self.tienda.estado_atencion(self.a_las(19, 18, 30))
        self.assertFalse(estado["abierto"])
        self.assertEqual(estado["detalle"], "Abre mañana a las 9:00 a. m.")

    def test_martes_en_la_noche_abre_el_lunes(self):
        estado = self.tienda.estado_atencion(self.a_las(20, 20))
        self.assertEqual(estado["detalle"], "Abre el lunes a las 9:00 a. m.")

    def test_sin_horario_no_muestra_estado(self):
        otra = crear_tienda("tienda2", "Tienda Dos", "922222222")
        self.assertIsNone(otra.estado_atencion())

    def test_perfil_publico_muestra_el_horario(self):
        respuesta = self.client.get(reverse("tiendas:perfil", args=[self.tienda.pk]))
        self.assertContains(respuesta, "Horario del local")
        self.assertContains(respuesta, "9:00 a. m. – 6:00 p. m.")
        self.assertContains(respuesta, "Lunes y martes")  # días iguales juntos


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
        self.assertEqual(estado["detalle"], "Cierra por refrigerio a la 1:00 p. m.")

    def test_durante_el_refrigerio(self):
        estado = self.estado(14)
        self.assertFalse(estado["abierto"])
        self.assertTrue(estado["refrigerio"])
        self.assertEqual(estado["detalle"], "Vuelve a abrir a las 3:00 p. m.")

    def test_en_la_tarde(self):
        estado = self.estado(16, 30)
        self.assertTrue(estado["abierto"])
        self.assertEqual(estado["detalle"], "Cierra a las 10:00 p. m.")

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


class LeerHoraTests(SimpleTestCase):
    """Las horas se escriben como las dice la gente."""

    def test_formas_validas(self):
        from .forms import leer_hora
        casos = {"8 am": time(8), "8:30 p. m.": time(20, 30), "8.30pm": time(20, 30), "20:30": time(20, 30),
                 "12 m": time(12), "12:00 p. m.": time(12), "12:30 a. m.": time(0, 30), "9 P.M.": time(21)}
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(leer_hora(texto), esperado)

    def test_formas_invalidas(self):
        from django.core.exceptions import ValidationError

        from .forms import leer_hora
        for texto in ("8", "8:75", "hola", "13 pm"):
            with self.subTest(texto=texto), self.assertRaises(ValidationError):
                leer_hora(texto)

    def test_sugerencias_cada_hora(self):
        from .forms import HORAS_SUGERIDAS
        self.assertEqual(HORAS_SUGERIDAS[:3], ["6:00 a. m.", "7:00 a. m.", "8:00 a. m."])
        self.assertEqual(len(HORAS_SUGERIDAS), 24)


class AmpliarImagenesTests(TestCase):
    def test_logo_del_perfil_se_puede_ampliar(self):
        tienda = crear_tienda()
        tienda.logo = "tiendas/logos/logo.webp"  # solo se revisa el HTML, no hace falta el archivo
        tienda.save(update_fields=["logo"])
        respuesta = self.client.get(reverse("tiendas:perfil", args=[tienda.pk]))
        self.assertContains(respuesta, 'data-ampliar="/media/tiendas/logos/logo.webp"')
        self.assertContains(respuesta, 'id="modal-imagen"')
