"""QR de la página (consola → «QR de la página»): cartel, pantalla para la feria, descargas y contador de visitas."""
import segno
from django.test import TestCase, override_settings
from django.urls import reverse

from administracion.test_consola import crear_admin, crear_cliente

from . import qr
from .models import VisitaQR

SITIO = "https://feria-nexalys.trycloudflare.com"


@override_settings(SITIO_URL=SITIO)
class QrPaginaTests(TestCase):
    def setUp(self):
        self.admin = crear_admin()
        self.client.force_login(self.admin)

    def test_el_qr_lleva_al_inicio_con_la_marca(self):
        self.assertEqual(qr.enlace(), f"{SITIO}/?desde=qr")
        self.assertEqual(qr.enlace_corto(), "feria-nexalys.trycloudflare.com")
        self.assertEqual(qr.crear().error, "Q")
        self.assertEqual(qr.crear().matrix, segno.make(f"{SITIO}/?desde=qr", error="q").matrix)

    def test_pagina_de_la_consola(self):
        respuesta = self.client.get(reverse("administracion:qr"))
        self.assertContains(respuesta, '<h1 class="h3 mb-0">QR de la página</h1>')
        self.assertContains(respuesta, '<h2 class="cartel-qr__nombre">NEXALYS Tec</h2>')
        self.assertContains(respuesta, "<svg viewBox=")
        self.assertContains(respuesta, f'data-url="{SITIO}/?desde=qr"')
        self.assertContains(respuesta, f'href="{reverse("administracion:qr_pantalla")}"')
        self.assertContains(respuesta, "data-imprimir")
        self.assertNotContains(respuesta, "todavía no sirve en otros celulares")
        # En el menú lateral de la consola, marcado como la sección actual.
        self.assertContains(respuesta, 'aria-current="page"><i class="bi bi-qr-code" aria-hidden="true"></i>QR de la página</a>')

    def test_el_cartel_descargado_lleva_el_logo_completo(self):
        # El logo es un SVG sin ancho ni alto: al bajar el PNG solo salía un pedazo («hoja» oscura).
        self.assertContains(self.client.get(reverse("administracion:qr")), "cartel-qr__logo--marca")
        from django.contrib.staticfiles import finders
        with open(finders.find("js/cartel_qr.js"), encoding="utf-8") as archivo:
            codigo = archivo.read()
        for texto in ("function cargarLogo(img)", 'raiz.setAttribute("width", "512")', 'classList.contains("cartel-qr__logo--marca")'):
            self.assertIn(texto, codigo)

    @override_settings(SITIO_URL="http://127.0.0.1:8000")
    def test_aviso_si_el_qr_apunta_a_la_pc(self):
        self.assertTrue(qr.es_local())
        self.assertContains(self.client.get(reverse("administracion:qr")), "todavía no sirve en otros celulares")
        self.assertContains(self.client.get(reverse("administracion:qr_pantalla")), "solo funciona en esta computadora")

    def test_pantalla_para_la_feria(self):
        respuesta = self.client.get(reverse("administracion:qr_pantalla"))
        self.assertContains(respuesta, "Escanea y prueba <span>NEXALYS Tec</span>")
        self.assertContains(respuesta, '<p class="pantalla-qr__enlace">feria-nexalys.trycloudflare.com</p>')
        self.assertContains(respuesta, f'data-url="{reverse("administracion:qr_visitas")}"')
        self.assertNotContains(respuesta, 'class="cabecera-marca')  # sin cabecera ni pie
        self.assertNotContains(respuesta, "solo funciona en esta computadora")

    def test_descargar_png_y_svg(self):
        png = self.client.get(reverse("administracion:qr_descargar", args=["png"]))
        self.assertEqual(png["Content-Type"], "image/png")
        self.assertTrue(png.content.startswith(b"\x89PNG"))
        self.assertEqual(png["Content-Disposition"], 'attachment; filename="qr-nexalys-tec.png"')
        svg = self.client.get(reverse("administracion:qr_descargar", args=["svg"]))
        self.assertEqual(svg["Content-Type"], "image/svg+xml")
        self.assertEqual(self.client.get("/administracion/qr.exe").status_code, 404)

    def test_solo_el_administrador(self):
        self.client.force_login(crear_cliente())
        for nombre in ("qr", "qr_pantalla", "qr_visitas"):
            self.assertEqual(self.client.get(reverse(f"administracion:{nombre}")).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("administracion:qr")).status_code, 302)


class ContadorVisitasTests(TestCase):
    def test_cuenta_una_vez_por_persona_y_limpia_la_direccion(self):
        respuesta = self.client.get("/?desde=qr")
        self.assertRedirects(respuesta, reverse("inicio"))
        self.client.get("/?desde=qr")  # el mismo celular vuelve a escanear
        self.assertEqual(VisitaQR.objects.count(), 1)
        otro = self.client_class()
        otro.get("/?desde=qr")
        self.assertEqual(VisitaQR.objects.count(), 2)

    def test_el_inicio_normal_no_cuenta(self):
        self.client.get(reverse("inicio"))
        self.client.get("/?desde=otra-cosa")
        self.assertEqual(VisitaQR.objects.count(), 0)

    def test_no_cuenta_al_administrador(self):
        self.client.force_login(crear_admin())
        self.client.get("/?desde=qr")
        self.assertEqual(VisitaQR.objects.count(), 0)

    def test_contador_y_reinicio(self):
        VisitaQR.objects.create()
        VisitaQR.objects.create()
        self.client.force_login(crear_admin())
        self.assertEqual(self.client.get(reverse("administracion:qr_visitas")).json(), {"total": 2, "hoy": 2})
        self.assertContains(self.client.get(reverse("administracion:qr")), "<strong>2</strong> en total")
        self.assertEqual(self.client.get(reverse("administracion:qr_reiniciar")).status_code, 405)
        respuesta = self.client.post(reverse("administracion:qr_reiniciar"), follow=True)
        self.assertContains(respuesta, "Contador en cero: se borraron 2 visitas.")
        self.assertEqual(VisitaQR.objects.count(), 0)
