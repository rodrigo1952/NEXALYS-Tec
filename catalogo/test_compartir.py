"""Compartir mejor: enlace en el mensaje de WhatsApp, botón «Compartir» y vista previa con foto."""
import shutil
import tempfile
from decimal import Decimal
from urllib.parse import unquote

from django.contrib.staticfiles import finders
from django.test import override_settings
from django.urls import reverse

from .imagenes import url_miniatura
from .test_fotos import foto
from .tests import BaseCatalogo

CARPETA_MEDIA = tempfile.mkdtemp()
SITIO = "https://nexalys.pythonanywhere.com"


@override_settings(MEDIA_ROOT=CARPETA_MEDIA, SITIO_URL=SITIO)
class CompartirTests(BaseCatalogo):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def test_mensaje_de_whatsapp_con_el_enlace_al_final(self):
        producto = self.crear_producto(nombre="Laptop Lenovo IdeaPad", precio=Decimal("1199"))
        self.assertEqual(
            producto.mensaje_whatsapp(),
            f'Hola, me interesa el producto "Laptop Lenovo IdeaPad" (S/ 1,199.00) que vi en NEXALYS Tec: '
            f"{SITIO}/catalogo/producto/{producto.pk}/",
        )
        self.assertIn(f"{SITIO}/catalogo/producto/{producto.pk}/", unquote(producto.enlace_whatsapp()))

    def test_enlaces_publicos(self):
        producto = self.crear_producto()
        self.assertEqual(producto.enlace_publico(), f"{SITIO}/catalogo/producto/{producto.pk}/")
        self.assertEqual(self.tienda.enlace_publico(), f"{SITIO}/tiendas/{self.tienda.pk}/")
        self.assertEqual(self.tienda.get_absolute_url(), reverse("tiendas:perfil", args=[self.tienda.pk]))

    def test_boton_compartir_en_el_detalle(self):
        producto = self.crear_producto(nombre="Galaxy A15")
        respuesta = self.client.get(reverse("catalogo:detalle", args=[producto.pk]))
        self.assertContains(respuesta, f'data-url="{SITIO}/catalogo/producto/{producto.pk}/"')
        self.assertContains(respuesta, 'data-titulo="Galaxy A15" data-texto="Galaxy A15 en NEXALYS Tec"')
        self.assertContains(respuesta, '<i class="bi bi-share" aria-hidden="true"></i> Compartir')
        self.assertContains(respuesta, 'id="aviso-compartir"', count=1)

    def test_boton_compartir_en_la_tienda(self):
        respuesta = self.client.get(reverse("tiendas:perfil", args=[self.tienda.pk]))
        self.assertContains(respuesta, f'data-url="{SITIO}/tiendas/{self.tienda.pk}/"')
        self.assertContains(respuesta, 'data-texto="Mira los productos de Tienda Uno en NEXALYS Tec"')

    def test_vista_previa_del_producto_con_foto_jpeg(self):
        producto = self.crear_producto(nombre="Galaxy A15", precio=Decimal("699.90"), imagen=foto("principal.png"))
        respuesta = self.client.get(reverse("catalogo:detalle", args=[producto.pk]))
        jpeg = url_miniatura(producto.imagen, "compartir")
        self.assertTrue(jpeg.endswith(".jpg"))
        self.assertContains(respuesta, f'<meta property="og:image" content="{SITIO}{jpeg}">')
        self.assertContains(respuesta, '<meta property="og:title" content="Galaxy A15 · S/ 699.90">')
        self.assertContains(respuesta, '<meta property="og:type" content="product">')
        self.assertContains(respuesta, f'<meta property="og:url" content="{SITIO}/catalogo/producto/{producto.pk}/">')
        self.assertContains(respuesta, '<meta name="description" content="Galaxy A15 a S/ 699.90 en Tienda Uno, Quillabamba.')

    def test_vista_previa_sin_foto_no_pone_imagen(self):
        producto = self.crear_producto()
        respuesta = self.client.get(reverse("catalogo:detalle", args=[producto.pk]))
        self.assertNotContains(respuesta, "og:image")
        self.assertContains(respuesta, '<meta property="og:title"', count=1)

    def test_vista_previa_de_la_tienda_con_su_logo(self):
        self.tienda.logo = foto("logo.png")
        self.tienda.save()
        respuesta = self.client.get(reverse("tiendas:perfil", args=[self.tienda.pk]))
        self.assertContains(respuesta, '<meta property="og:title" content="Tienda Uno · NEXALYS Tec">')
        self.assertContains(respuesta, f'<meta property="og:image" content="{SITIO}{url_miniatura(self.tienda.logo, "compartir")}">')

    def test_las_demas_paginas_tienen_vista_previa_general(self):
        respuesta = self.client.get(reverse("catalogo:catalogo"))
        self.assertContains(respuesta, '<meta property="og:title" content="NEXALYS Tec">')
        self.assertContains(respuesta, '<meta name="description" content="Productos tecnológicos de las tiendas de Quillabamba')

    def test_script_compartir(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, "js/compartir.js")
        with open(finders.find("js/compartir.js"), encoding="utf-8") as archivo:
            codigo = archivo.read()
        for texto in ("navigator.share", "(pointer: coarse)", "clipboard.writeText", "AbortError", "Enlace copiado"):
            self.assertIn(texto, codigo)
