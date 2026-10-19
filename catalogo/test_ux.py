"""Pruebas de las mejoras de UX/UI (actividad 07)."""

from decimal import Decimal

from django.test import SimpleTestCase
from django.urls import reverse

from .templatetags.formato import soles
from .tests import BaseCatalogo


class FiltroSolesTests(SimpleTestCase):
    def test_separador_de_miles_y_dos_decimales(self):
        self.assertEqual(soles(Decimal("2499")), "S/ 2,499.00")
        self.assertEqual(soles(Decimal("1234567.5")), "S/ 1,234,567.50")
        self.assertEqual(soles(Decimal("65.2")), "S/ 65.20")

    def test_valor_vacio(self):
        self.assertEqual(soles(None), "")


class MejorasInterfazTests(BaseCatalogo):
    def test_precio_con_miles_en_el_catalogo(self):
        self.crear_producto(nombre="Laptop gamer", precio=Decimal("4599.90"))
        self.assertContains(self.client.get(reverse("catalogo:catalogo")), "S/ 4,599.90")

    def test_menu_marca_la_seccion_actual(self):
        respuesta = self.client.get(reverse("catalogo:catalogo"))
        self.assertContains(respuesta, f'active" aria-current="page" href="{reverse("catalogo:catalogo")}"')
        self.assertNotContains(respuesta, f'active" aria-current="page" href="{reverse("inicio")}"')

    def test_mensajes_se_pueden_cerrar(self):
        self.client.force_login(self.tienda.usuario)
        producto = self.crear_producto()
        respuesta = self.client.post(reverse("catalogo:eliminar", args=[producto.pk]), follow=True)
        self.assertContains(respuesta, "alert-dismissible")
        self.assertContains(respuesta, 'class="btn-close"')
        self.assertContains(respuesta, "data-autocierre")

    def test_formularios_evitan_el_doble_envio(self):
        self.assertContains(self.client.get(reverse("inicio")), "form.dataset.enviando")

    def test_pie_de_pagina(self):
        self.assertContains(self.client.get(reverse("inicio")), "IESPP Urusayhua")

    def test_pagina_404_propia(self):
        respuesta = self.client.get("/esta-pagina-no-existe/")
        self.assertEqual(respuesta.status_code, 404)
        self.assertTemplateUsed(respuesta, "404.html")
        self.assertContains(respuesta, "No encontramos esta página", status_code=404)
