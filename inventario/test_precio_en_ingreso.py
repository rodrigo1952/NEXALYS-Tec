"""
Ingreso con otro costo: el costo se promedia y el precio de venta solo cambia si la tienda lo pide
(un solo precio por producto). Si el producto queda sin ganancia, se avisa.
"""

from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from catalogo.tests import BaseCatalogo

from . import servicios
from .models import FichaInventario, LineaIngreso
from .servicios import LineaRecibida
from .test_ingresos import datos_ingreso


class PrecioEnIngresoTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        # Ejemplo de la tienda: tenía 5 a S/ 1000 de costo y lo vende a S/ 1200.
        self.producto = self.crear_producto(nombre="Laptop Lenovo", precio=Decimal("1200.00"), stock=5)
        FichaInventario.objects.create(producto=self.producto, costo=Decimal("1000.00"))
        self.client.force_login(self.tienda.usuario)
        self.url = reverse("inventario:ingreso_nuevo")

    def enviar(self, costo, precio_venta=""):
        datos = datos_ingreso([(self.producto, 5, costo)], **{"lineas-0-precio_venta": precio_venta})
        return self.client.post(self.url, datos, follow=True)

    def test_sin_precio_nuevo_el_precio_de_venta_no_cambia(self):
        self.enviar("1500")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.precio, Decimal("1200.00"))
        self.assertEqual(self.producto.stock, 10)
        self.assertEqual(self.producto.ficha.costo, Decimal("1250.00"))  # (5×1000 + 5×1500) / 10
        linea = LineaIngreso.objects.get()
        self.assertIsNone(linea.precio_nuevo)

    def test_avisa_si_el_producto_queda_sin_ganancia(self):
        respuesta = self.enviar("1500")
        self.assertContains(respuesta, "«Laptop Lenovo» se vende a S/ 1,200.00 y ahora te cuesta S/ 1,250.00")
        self.assertContains(respuesta, "no te deja ganancia")

    def test_con_precio_nuevo_cambia_para_todo_el_stock_y_queda_anotado(self):
        respuesta = self.enviar("1500", "1650")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.precio, Decimal("1650.00"))
        linea = LineaIngreso.objects.get()
        self.assertEqual((linea.precio_anterior, linea.precio_nuevo), (Decimal("1200.00"), Decimal("1650.00")))
        self.assertContains(respuesta, "cambiaste el precio de venta de 1 producto.")
        self.assertContains(respuesta, "Precio de venta: S/ 1,200.00 → <strong class=\"text-body\">S/ 1,650.00</strong>")
        self.assertNotContains(respuesta, "no te deja ganancia")
        # Al anular, se avisa que el precio no vuelve solo.
        anular = self.client.get(reverse("inventario:ingreso_anular", args=[linea.ingreso_id]))
        self.assertContains(anular, "no vuelven solos")

    def test_el_mismo_precio_no_cuenta_como_cambio(self):
        self.enviar("900", "1200")
        self.assertIsNone(LineaIngreso.objects.get().precio_nuevo)

    def test_en_oferta_el_precio_normal_debe_ser_mayor_que_la_oferta(self):
        self.producto.precio_oferta = Decimal("1100.00")
        self.producto.oferta_hasta = timezone.localdate() + timedelta(days=3)
        self.producto.save()
        respuesta = self.enviar("1000", "1050")
        self.assertContains(respuesta, "Está en oferta a S/ 1,100.00: el precio normal debe ser mayor.")
        self.assertFalse(LineaIngreso.objects.exists())

    def test_precio_sin_producto_pide_elegir_el_producto(self):
        datos = datos_ingreso([], **{"lineas-0-precio_venta": "50"})
        self.assertContains(self.client.post(self.url, datos), "Elige el producto.")

    def test_el_formulario_lleva_los_datos_para_calcular_la_ganancia(self):
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, 'data-precio-normal="1200.00"')
        self.assertContains(respuesta, 'data-costo="1000.00"')
        self.assertContains(respuesta, 'name="lineas-0-precio_venta"')
        self.assertContains(respuesta, "Costo promedio después del ingreso")
        self.assertContains(respuesta, "Nuevo precio de venta (opcional)")

    def test_servicio_ventas_sin_ganancia(self):
        servicios.registrar_ingreso(self.tienda, self.tienda.usuario, [LineaRecibida(self.producto.pk, 5, Decimal("1500"))])
        self.producto.refresh_from_db()
        self.assertEqual(servicios.ventas_sin_ganancia([self.producto]),
                         [(self.producto, Decimal("1200.00"), Decimal("1250.00"))])
        sin_ficha = self.crear_producto(nombre="Funda")
        self.assertEqual(servicios.ventas_sin_ganancia([sin_ficha]), [])
