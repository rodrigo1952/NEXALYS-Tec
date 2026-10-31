"""Perfil público: aviso claro del local, horario agrupado, productos A→Z y logo editable."""

import io
import shutil
import tempfile
from datetime import datetime, time
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from catalogo.models import Categoria, Marca, Producto

from .models import HorarioDia, etiqueta_dias
from .tests import crear_tienda

CARPETA_MEDIA = tempfile.mkdtemp()


def imagen(nombre="logo.png"):
    archivo = io.BytesIO()
    Image.new("RGB", (300, 300), "blue").save(archivo, "PNG")
    return SimpleUploadedFile(nombre, archivo.getvalue(), content_type="image/png")


class EtiquetaDiasTests(SimpleTestCase):
    def test_nombres_de_dias(self):
        self.assertEqual(etiqueta_dias([0, 1, 2, 3, 4, 5]), "Lunes a sábado")
        self.assertEqual(etiqueta_dias([5, 6]), "Sábado y domingo")
        self.assertEqual(etiqueta_dias([0, 1, 2, 4]), "Lunes a miércoles y viernes")
        self.assertEqual(etiqueta_dias(range(7)), "Todos los días")


class PerfilPublicoTests(TestCase):
    """El lunes 19/10/2026; horas de Perú."""

    def setUp(self):
        self.tienda = crear_tienda()
        for dia in range(6):
            HorarioDia.objects.create(tienda=self.tienda, dia=dia, abre=time(8), cierra=time(21))
        self.url = reverse("tiendas:perfil", args=[self.tienda.pk])

    def en(self, dia, hora):
        return mock.patch("django.utils.timezone.now", return_value=timezone.make_aware(datetime(2026, 10, dia, hora)))

    def test_horario_agrupado_con_hoy(self):
        filas = self.tienda.horario_agrupado(timezone.make_aware(datetime(2026, 10, 25, 10)))  # domingo
        self.assertEqual([(f["dias"], f["texto"], f["hoy"]) for f in filas], [
            ("Lunes a sábado", "8:00 a. m. – 9:00 p. m.", False),
            ("Domingo", "Cerrado", True),
        ])

    def test_aviso_de_local_cerrado_explica_que_la_pagina_sigue(self):
        with self.en(25, 10):  # domingo: cerrado
            respuesta = self.client.get(self.url)
        self.assertContains(respuesta, "El local (tienda física) está")
        self.assertContains(respuesta, "<strong>CERRADO</strong> ahora.", html=False)
        self.assertContains(respuesta, "Abre mañana a las 8:00 a. m.")
        self.assertContains(respuesta, "puedes ver sus productos y escribirle por WhatsApp <strong>a cualquier hora</strong>")
        self.assertContains(respuesta, "Lunes a sábado")
        self.assertContains(respuesta, '<span class="horario-agrupado__hoy">Hoy</span>')

    def test_aviso_de_local_abierto(self):
        with self.en(19, 10):
            respuesta = self.client.get(self.url)
        self.assertContains(respuesta, "<strong>ABIERTO</strong> ahora.", html=False)
        self.assertContains(respuesta, "Cierra a las 9:00 p. m.")
        self.assertNotContains(respuesta, "a cualquier hora")

    def test_el_detalle_del_producto_usa_el_mismo_aviso(self):
        producto = Producto.objects.create(
            tienda=self.tienda, categoria=Categoria.objects.get(nombre="Celulares"),
            marca=Marca.objects.get(nombre="Samsung"), nombre="Galaxy A15", precio="700.00", stock=3,
        )
        with self.en(25, 10):
            respuesta = self.client.get(reverse("catalogo:detalle", args=[producto.pk]))
        self.assertContains(respuesta, "estado-local--compacto")
        self.assertContains(respuesta, "El local (tienda física) está")

    def test_productos_de_la_a_a_la_z(self):
        categoria, marca = Categoria.objects.get(nombre="Celulares"), Marca.objects.get(nombre="Samsung")
        for nombre in ("zeta phone", "Alfa Tab", "monitor Beta"):
            Producto.objects.create(tienda=self.tienda, categoria=categoria, marca=marca, nombre=nombre, precio="10", stock=1)
        nombres = [p.nombre for p in self.client.get(self.url).context["productos"]]
        self.assertEqual(nombres, ["Alfa Tab", "monitor Beta", "zeta phone"])
        self.client.force_login(self.tienda.usuario)
        nombres = [p.nombre for p in self.client.get(reverse("catalogo:mis_productos")).context["pagina"]]
        self.assertEqual(nombres, ["Alfa Tab", "monitor Beta", "zeta phone"])


@override_settings(MEDIA_ROOT=CARPETA_MEDIA)
class LogoDesdeElMenuTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.tienda = crear_tienda()
        self.client.force_login(self.tienda.usuario)
        self.url = reverse("tiendas:logo")

    def test_el_circulo_abre_la_ventana_del_logo(self):
        respuesta = self.client.get(reverse("mi_cuenta"))
        self.assertContains(respuesta, 'id="cambiar-logo"')
        self.assertContains(respuesta, 'id="modal-logo"')
        self.assertContains(respuesta, "Guardar logo")
        self.assertContains(respuesta, "Elegir otra")
        self.assertNotContains(respuesta, "Ver mi tienda pública")

    def test_cambiar_y_quitar_el_logo_sin_contrasena(self):
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(self.url, {"logo": imagen(), "next": reverse("mi_cuenta")})
        self.assertRedirects(respuesta, reverse("mi_cuenta"))
        self.tienda.refresh_from_db()
        self.assertTrue(self.tienda.logo.name.endswith(".webp"))
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.url, {"quitar": "1"})
        self.tienda.refresh_from_db()
        self.assertFalse(self.tienda.logo)

    def test_archivo_que_no_es_imagen(self):
        archivo = SimpleUploadedFile("logo.txt", b"hola", content_type="text/plain")
        respuesta = self.client.post(self.url, {"logo": archivo}, follow=True)
        self.assertContains(respuesta, "No se pudo cambiar el logo")
        self.tienda.refresh_from_db()
        self.assertFalse(self.tienda.logo)

    def test_otros_no_pueden(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 405)
        respuesta = self.client.post(self.url, {"quitar": "1"})
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("login"), respuesta["Location"])
