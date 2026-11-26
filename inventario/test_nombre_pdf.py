"""
Nov 2026: al «Guardar como PDF», el archivo toma el título de la página. La nota de venta y el ingreso
empiezan con el nombre de la tienda («Selva Byte - Nota de venta N.° 00007») para que se ordenen por tienda.
"""

from decimal import Decimal

from django.urls import reverse

from catalogo.tests import BaseCatalogo

from . import servicios
from .models import FichaInventario, Proveedor
from .servicios import LineaPedida, LineaRecibida


class NombreDelPdfTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.producto = self.crear_producto(nombre="Galaxy A15", precio=Decimal("700.00"), stock=5)
        FichaInventario.objects.create(producto=self.producto, costo=Decimal("100.00"))
        self.client.force_login(self.tienda.usuario)

    def test_nota_de_venta_lleva_el_nombre_de_la_tienda(self):
        venta = servicios.registrar_venta(self.tienda, self.tienda.usuario, [LineaPedida(self.producto.pk, 1)])
        respuesta = self.client.get(reverse("inventario:venta_detalle", args=[venta.pk]))
        self.assertContains(respuesta, f"<title>{self.tienda.nombre} - Nota de venta N.° 00001</title>", html=False)

    def test_ingreso_lleva_el_nombre_de_la_tienda(self):
        proveedor = Proveedor.objects.create(tienda=self.tienda, nombre="Distribuidora Cusco")
        ingreso = servicios.registrar_ingreso(self.tienda, self.tienda.usuario,
                                              [LineaRecibida(self.producto.pk, 2, Decimal("110.00"))],
                                              proveedor=proveedor, documento="F001-12")
        respuesta = self.client.get(reverse("inventario:ingreso_detalle", args=[ingreso.pk]))
        self.assertContains(respuesta, f"<title>{self.tienda.nombre} - Ingreso N.° 00001</title>", html=False)
