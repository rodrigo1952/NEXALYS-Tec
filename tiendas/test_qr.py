"""QR de la tienda: cartel para imprimir y descargas PNG/SVG con el enlace a su página."""
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Tienda
from .tests import crear_tienda
from . import qr

SITIO = "https://nexalys.pythonanywhere.com"


@override_settings(SITIO_URL=SITIO)
class CodigoQrTests(TestCase):
    def setUp(self):
        self.tienda = crear_tienda()
        self.client.force_login(self.tienda.usuario)

    def test_el_qr_lleva_a_la_pagina_de_la_tienda(self):
        codigo = qr.crear(self.tienda)
        self.assertEqual(codigo.error, "Q")
        self.assertEqual(self.tienda.enlace_publico(), f"{SITIO}/tiendas/{self.tienda.pk}/")
        # segno no lee QR: se comprueba que el contenido codificado es el enlace, comparando con uno hecho a mano.
        import segno

        self.assertEqual(codigo.matrix, segno.make(f"{SITIO}/tiendas/{self.tienda.pk}/", error="q").matrix)

    def test_cartel_para_imprimir(self):
        respuesta = self.client.get(reverse("tiendas:qr"))
        self.assertContains(respuesta, '<h2 class="cartel-qr__nombre">Tienda Uno</h2>')
        self.assertContains(respuesta, "Escanéame con la cámara de tu celular")
        self.assertContains(respuesta, f"{SITIO}/tiendas/{self.tienda.pk}/")
        self.assertContains(respuesta, '<svg viewBox=')
        self.assertContains(respuesta, "data-imprimir")
        self.assertNotContains(respuesta, "solo funciona en esta computadora")

    @override_settings(SITIO_URL="http://127.0.0.1:8000")
    def test_aviso_si_el_qr_apunta_a_la_pc(self):
        self.assertContains(self.client.get(reverse("tiendas:qr")), "solo funciona en esta computadora")

    def test_descargar_png_y_svg(self):
        png = self.client.get(reverse("tiendas:qr_descargar", args=["png"]))
        self.assertEqual(png["Content-Type"], "image/png")
        self.assertTrue(png.content.startswith(b"\x89PNG"))
        self.assertEqual(png["Content-Disposition"], 'attachment; filename="qr-tienda-uno.png"')
        svg = self.client.get(reverse("tiendas:qr_descargar", args=["svg"]))
        self.assertEqual(svg["Content-Type"], "image/svg+xml")
        self.assertIn(b"<svg", svg.content)
        self.assertEqual(self.client.get("/tiendas/panel/qr.exe").status_code, 404)

    def test_acceso_desde_el_panel(self):
        self.assertContains(self.client.get(reverse("tiendas:panel")), f'href="{reverse("tiendas:qr")}"')

    def test_solo_tiendas_activas(self):
        self.tienda.estado = Tienda.Estado.PENDIENTE
        self.tienda.save()
        self.assertNotContains(self.client.get(reverse("tiendas:panel")), "Código QR de tu tienda")
        self.assertEqual(self.client.get(reverse("tiendas:qr")).status_code, 302)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("tiendas:qr")).status_code, 302)
