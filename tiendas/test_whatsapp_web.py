"""
Botones de WhatsApp: en el celular se usa wa.me (abre la app directo en el chat); en la computadora,
static/js/whatsapp.js muestra un menú: «WhatsApp Web» (pestaña nueva) o «App de WhatsApp» (whatsapp://).
"""

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


def whatsapp_js():
    with open(finders.find("js/whatsapp.js"), encoding="utf-8") as archivo:
        return archivo.read()


class WhatsAppEnLaComputadoraTests(TestCase):
    def test_el_script_se_carga_en_todas_las_paginas(self):
        for url in (reverse("inicio"), reverse("catalogo:catalogo"), reverse("tiendas:cercanas")):
            self.assertContains(self.client.get(url), "js/whatsapp.js")

    def test_menu_con_whatsapp_web_y_la_app(self):
        codigo = whatsapp_js()
        self.assertIn('"whatsapp://send?phone=" : "https://web.whatsapp.com/send?phone="', codigo)
        self.assertIn('a[href^="https://wa.me/"]', codigo)
        for texto in ("¿Dónde abrir el chat?", "WhatsApp Web", "App de WhatsApp",
                      "Recordar mi elección en este navegador", "Cambiar", "Usar WhatsApp Web"):
            self.assertIn(texto, codigo)
        self.assertIn('var CLAVE = "nexalys_whatsapp_modo";', codigo)

    def test_en_el_celular_se_deja_wa_me(self):
        codigo = whatsapp_js()
        self.assertIn("if (!esComputadora()) {", codigo)
        self.assertIn("/Android|iPhone|iPad|iPod|Mobile|Silk|Kindle/i", codigo)

    def test_se_mantiene_la_politica_de_seguridad_de_django(self):
        # No se pudo reutilizar la pestaña de WhatsApp Web, así que no hace falta relajar esta política.
        respuesta = self.client.get(reverse("catalogo:catalogo"))
        self.assertEqual(respuesta["Cross-Origin-Opener-Policy"], "same-origin")


class CambiarLaEleccionTests(TestCase):
    """Nov 2026: la elección (Web o app) se puede cambiar siempre; «Recordar» viene desmarcado."""

    def test_recordar_viene_desmarcado(self):
        codigo = whatsapp_js()
        self.assertIn('<input type="checkbox" class="form-check-input"> Recordar mi elección', codigo)
        self.assertNotIn("form-check-input\" checked>", codigo)

    def test_el_aviso_dura_15_segundos_y_se_pausa_con_el_mouse(self):
        codigo = whatsapp_js()
        self.assertIn("setTimeout(cerrarAviso, 15000)", codigo)
        self.assertIn('aviso.addEventListener("mouseenter", pausar);', codigo)
        self.assertIn('cambiar.className = "btn btn-outline-success btn-sm py-0";', codigo)

    def test_texto_bajo_el_boton_en_producto_y_tienda(self):
        from catalogo.models import Categoria, Marca, Producto
        from .tests import crear_tienda

        tienda = crear_tienda()
        producto = Producto.objects.create(
            tienda=tienda, categoria=Categoria.objects.get_or_create(nombre="Celulares")[0],
            marca=Marca.objects.get_or_create(nombre="Samsung")[0], nombre="Galaxy", precio=500, stock=2,
        )
        for url in (reverse("catalogo:detalle", args=[producto.pk]), reverse("tiendas:perfil", args=[tienda.pk])):
            self.assertContains(self.client.get(url), '<p class="modo-whatsapp" data-modo-whatsapp hidden></p>', html=True)
        codigo = whatsapp_js()
        self.assertIn('document.querySelectorAll("[data-modo-whatsapp]")', codigo)
        self.assertIn("El chat se abre en", codigo)
        self.assertIn("Listo: la próxima vez te preguntaremos dónde abrir el chat.", codigo)
