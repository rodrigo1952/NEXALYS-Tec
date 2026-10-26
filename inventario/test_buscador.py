"""Buscador de productos en Nuevo ingreso, Nueva venta y Nuevo ajuste."""

from decimal import Decimal

from django.urls import reverse

from catalogo.tests import BaseCatalogo

from .forms import sin_tildes
from .models import FichaInventario

PAGINAS = ("inventario:ingreso_nuevo", "inventario:venta_nueva", "inventario:ajuste_nuevo")


class BuscadorDeProductosTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.producto = self.crear_producto(nombre="Cámara Galaxy Ñandú", precio=Decimal("50.00"), stock=5)
        FichaInventario.objects.create(producto=self.producto, codigo="CAM-01")
        self.client.force_login(self.tienda.usuario)

    def test_sin_tildes(self):
        self.assertEqual(sin_tildes("Cámara ÑANDÚ"), "camara nandu")

    def test_las_tres_paginas_cargan_el_buscador(self):
        for nombre in PAGINAS:
            respuesta = self.client.get(reverse(nombre))
            self.assertContains(respuesta, "js/buscador_productos.js")
            self.assertContains(respuesta, "buscador-producto")
            # Se busca por nombre, código, marca y categoría, sin tildes.
            self.assertContains(respuesta, 'data-buscar="camara galaxy nandu cam-01 samsung celulares"')
            self.assertContains(respuesta, 'data-codigo="cam-01"')

    def test_cada_resultado_muestra_codigo_y_stock(self):
        self.assertContains(self.client.get(reverse("inventario:ingreso_nuevo")), "Cámara Galaxy Ñandú · Cód. CAM-01 · stock 5")
        # En ventas también el precio.
        self.assertContains(self.client.get(reverse("inventario:venta_nueva")), "Cámara Galaxy Ñandú · S/ 50.00 · Cód. CAM-01 · stock 5")

    def test_sin_codigo_ni_stock(self):
        self.crear_producto(nombre="Funda simple", stock=0)
        self.assertContains(self.client.get(reverse("inventario:ajuste_nuevo")), "Funda simple · agotado")

    def test_no_aparecen_productos_de_otra_tienda(self):
        self.crear_producto(tienda=self.otra_tienda, nombre="Producto ajeno")
        for nombre in PAGINAS:
            self.assertNotContains(self.client.get(reverse(nombre)), "Producto ajeno")
