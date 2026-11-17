"""
Nov 2026: el QR se comparte como imagen del cartel (static/js/cartel_qr.js) y los productos destacados
van primero en «Mis productos».
"""

from decimal import Decimal

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Marca, Producto

from .tests import crear_tienda


class CompartirCartelTests(TestCase):
    def setUp(self):
        self.tienda = crear_tienda()
        self.client.force_login(self.tienda.usuario)

    def test_panel_al_lado_del_cartel(self):
        html = self.client.get(reverse("tiendas:qr")).content.decode()
        self.assertIn('class="pagina-cartel"', html)
        self.assertIn("data-panel-cartel", html)
        self.assertLess(html.index('class="cartel-qr"'), html.index("data-panel-cartel"))
        for red in ("whatsapp", "facebook", "instagram", "sistema", "copiar", "descargar"):
            self.assertIn(f'data-compartir-red="{red}"', html)
        for texto in ("WhatsApp (imagen)", "Más (Telegram, correo…)", "Imprimir o guardar en PDF",
                      "Descargar cartel (PNG)", "SVG (para imprenta)", "js/cartel_qr.js", "data-aviso-cartel"):
            self.assertIn(texto, html)

    def test_el_script(self):
        with open(finders.find("js/cartel_qr.js"), encoding="utf-8") as archivo:
            codigo = archivo.read()
        for texto in ("navigator.canShare({ files: [archivo] })", 'lienzo.toBlob(listo, "image/png")', "var ANCHO = 1080, ALTO = 1350;",
                      "AbortError", "a.download = archivo.name", 'new ClipboardItem({ "image/png": archivo })',
                      "https://web.whatsapp.com/send?text=", "https://www.facebook.com/sharer/sharer.php?u=",
                      "https://www.instagram.com/", "pega la imagen con Ctrl + V"):
            self.assertIn(texto, codigo)


class DestacadosPrimeroTests(TestCase):
    def setUp(self):
        self.tienda = crear_tienda()
        self.client.force_login(self.tienda.usuario)
        categoria, _ = Categoria.objects.get_or_create(nombre="Audio")
        marca, _ = Marca.objects.get_or_create(nombre="Sony")
        for nombre, destacado in (("Audífonos A", False), ("Zeta parlante", True), ("Bocina B", False), ("Micro M", True)):
            Producto.objects.create(tienda=self.tienda, categoria=categoria, marca=marca, nombre=nombre,
                                    precio=Decimal("100"), stock=3, destacado=destacado)

    def test_primero_los_destacados_y_luego_a_z(self):
        respuesta = self.client.get(reverse("catalogo:mis_productos"))
        self.assertEqual([p.nombre for p in respuesta.context["pagina"]],
                         ["Micro M", "Zeta parlante", "Audífonos A", "Bocina B"])
        self.assertContains(respuesta, "fila-producto fila-producto--destacada", count=2)
        self.assertContains(respuesta, 'class="bi bi-star-fill estrella-destacado"', count=2)
        self.assertContains(respuesta, 'class="badge etiqueta-destacado"', count=2)  # azul marino con ★ cian
