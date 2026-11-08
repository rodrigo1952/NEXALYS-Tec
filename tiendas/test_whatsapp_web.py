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
            self.assertContains(self.client.get(url), "js/whatsapp.js?v=2")

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
