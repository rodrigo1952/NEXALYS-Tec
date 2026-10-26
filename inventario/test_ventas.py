"""Inventario · Etapa 2: ventas con varios productos, nota de venta y anulación."""

from decimal import Decimal

from django.urls import reverse

from catalogo.tests import BaseCatalogo

from . import servicios
from .models import FichaInventario, LineaVenta, Movimiento, Venta
from .servicios import LineaPedida


def datos_venta(lineas, **extra):
    """Arma el POST del formulario de venta: lineas = [(producto, cantidad, precio), ...]."""
    datos = {
        "lineas-TOTAL_FORMS": "10", "lineas-INITIAL_FORMS": "0",
        "lineas-MIN_NUM_FORMS": "0", "lineas-MAX_NUM_FORMS": "10",
        "metodo_pago": "efectivo", "cliente_nombre": "", "cliente_documento": "", "nota": "",
    }
    for i, (producto, cantidad, precio) in enumerate(lineas):
        datos[f"lineas-{i}-producto"] = str(producto.pk)
        datos[f"lineas-{i}-cantidad"] = str(cantidad)
        datos[f"lineas-{i}-precio"] = "" if precio is None else str(precio)
    datos.update(extra)
    return datos


class RegistrarVentaTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.celular = self.crear_producto(nombre="Galaxy A15", precio=Decimal("700.00"), stock=5)
        self.funda = self.crear_producto(nombre="Funda", precio=Decimal("20.00"), stock=10)

    def vender(self, *lineas, **extra):
        return servicios.registrar_venta(self.tienda, self.tienda.usuario, [LineaPedida(*l) for l in lineas], **extra)

    def test_venta_con_varios_productos_descuenta_stock_y_queda_en_el_kardex(self):
        venta = self.vender((self.celular.pk, 2), (self.funda.pk, 3))
        self.celular.refresh_from_db()
        self.funda.refresh_from_db()
        self.assertEqual((self.celular.stock, self.funda.stock), (3, 7))
        self.assertEqual(venta.total, Decimal("1460.00"))
        movimientos = Movimiento.objects.filter(tipo=Movimiento.Tipo.VENTA, venta=venta)
        self.assertEqual(sorted(m.cantidad for m in movimientos), [-3, -2])
        self.assertTrue(all("Venta N.° 00001" in m.nota for m in movimientos))

    def test_numeracion_por_tienda(self):
        self.assertEqual(self.vender((self.funda.pk, 1)).numero, 1)
        self.assertEqual(self.vender((self.funda.pk, 1)).numero, 2)
        otro = self.crear_producto(tienda=self.otra_tienda, nombre="Mouse", stock=3)
        venta_otra = servicios.registrar_venta(self.otra_tienda, self.otra_tienda.usuario, [LineaPedida(otro.pk, 1)])
        self.assertEqual(venta_otra.numero, 1)

    def test_sin_stock_no_se_guarda_nada(self):
        with self.assertRaises(servicios.StockInsuficiente):
            self.vender((self.funda.pk, 2), (self.celular.pk, 6))
        self.assertEqual(Venta.objects.count(), 0)
        self.funda.refresh_from_db()
        self.assertEqual(self.funda.stock, 10)

    def test_el_mismo_producto_en_dos_lineas_se_suma(self):
        with self.assertRaises(servicios.StockInsuficiente):
            self.vender((self.celular.pk, 3), (self.celular.pk, 3))
        venta = self.vender((self.celular.pk, 3), (self.celular.pk, 2))
        self.assertEqual(venta.lineas.count(), 2)
        self.celular.refresh_from_db()
        self.assertEqual(self.celular.stock, 0)

    def test_la_ultima_unidad_no_se_vende_dos_veces(self):
        unico = self.crear_producto(nombre="Último", stock=1)
        self.vender((unico.pk, 1))
        with self.assertRaises(servicios.StockInsuficiente):
            self.vender((unico.pk, 1))
        unico.refresh_from_db()
        self.assertEqual(unico.stock, 0)

    def test_precio_sugerido_y_precio_editado(self):
        venta = self.vender((self.celular.pk, 1), (self.funda.pk, 1, Decimal("15.00")))
        precios = dict(venta.lineas.values_list("producto_nombre", "precio_unitario"))
        self.assertEqual(precios, {"Galaxy A15": Decimal("700.00"), "Funda": Decimal("15.00")})
        self.assertEqual(venta.total, Decimal("715.00"))

    def test_guarda_el_costo_del_momento(self):
        FichaInventario.objects.create(producto=self.celular, costo=Decimal("550.00"))
        venta = self.vender((self.celular.pk, 1))
        FichaInventario.objects.filter(producto=self.celular).update(costo=Decimal("600.00"))
        self.assertEqual(venta.lineas.get().costo_unitario, Decimal("550.00"))

    def test_no_se_venden_productos_de_otra_tienda(self):
        ajeno = self.crear_producto(tienda=self.otra_tienda, nombre="Ajeno", stock=5)
        with self.assertRaises(servicios.OperacionNoPermitida):
            self.vender((ajeno.pk, 1))

    def test_anular_devuelve_el_stock_una_sola_vez(self):
        venta = self.vender((self.celular.pk, 2))
        servicios.anular_venta(venta, self.tienda.usuario, "Registrada por error")
        self.celular.refresh_from_db()
        self.assertEqual(self.celular.stock, 5)
        venta.refresh_from_db()
        self.assertTrue(venta.anulada)
        self.assertEqual(venta.motivo_anulacion, "Registrada por error")
        anulacion = Movimiento.objects.get(tipo=Movimiento.Tipo.ANULACION, venta=venta)
        self.assertEqual((anulacion.cantidad, anulacion.stock_resultante), (2, 5))
        with self.assertRaises(servicios.OperacionNoPermitida):
            servicios.anular_venta(venta, self.tienda.usuario, "Otra vez")

    def test_la_venta_se_conserva_si_se_elimina_el_producto(self):
        venta = self.vender((self.funda.pk, 1))
        self.funda.delete()
        linea = LineaVenta.objects.get(venta=venta)
        self.assertIsNone(linea.producto)
        self.assertEqual(linea.producto_nombre, "Funda")
        servicios.anular_venta(venta, self.tienda.usuario, "Prueba de anulación")  # no falla


class PaginasVentasTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.producto = self.crear_producto(nombre="Galaxy A15", precio=Decimal("700.00"), stock=5)
        self.client.force_login(self.tienda.usuario)

    def test_formulario_registra_la_venta(self):
        datos = datos_venta([(self.producto, 2, None)], metodo_pago="yape_plin", cliente_nombre="Ana Quispe",
                            cliente_documento="12345678")
        respuesta = self.client.post(reverse("inventario:venta_nueva"), datos)
        venta = Venta.objects.get()
        self.assertRedirects(respuesta, reverse("inventario:venta_detalle", args=[venta.pk]))
        self.assertEqual((venta.metodo_pago, venta.cliente_nombre, venta.total), ("yape_plin", "Ana Quispe", Decimal("1400.00")))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 3)

    def test_formulario_sin_productos_muestra_error(self):
        respuesta = self.client.post(reverse("inventario:venta_nueva"), datos_venta([]))
        self.assertContains(respuesta, "Agrega al menos un producto")
        self.assertEqual(Venta.objects.count(), 0)

    def test_formulario_sin_stock_muestra_error(self):
        respuesta = self.client.post(reverse("inventario:venta_nueva"), datos_venta([(self.producto, 9, None)]))
        self.assertContains(respuesta, "No hay stock suficiente")
        self.assertEqual(Venta.objects.count(), 0)

    def test_documento_invalido(self):
        respuesta = self.client.post(reverse("inventario:venta_nueva"),
                                     datos_venta([(self.producto, 1, None)], cliente_documento="123"))
        self.assertContains(respuesta, "El DNI tiene 8 dígitos")

    def test_el_formulario_solo_ofrece_productos_propios(self):
        ajeno = self.crear_producto(tienda=self.otra_tienda, nombre="Producto ajeno")
        respuesta = self.client.get(reverse("inventario:venta_nueva"))
        self.assertContains(respuesta, 'data-precio="700.00"')
        self.assertNotContains(respuesta, "Producto ajeno")
        respuesta = self.client.post(reverse("inventario:venta_nueva"), datos_venta([(ajeno, 1, None)]))
        self.assertEqual(Venta.objects.count(), 0)

    def test_nota_de_venta_imprimible(self):
        venta = servicios.registrar_venta(self.tienda, self.tienda.usuario, [LineaPedida(self.producto.pk, 1)])
        respuesta = self.client.get(reverse("inventario:venta_detalle", args=[venta.pk]))
        self.assertContains(respuesta, "NOTA DE VENTA")
        self.assertContains(respuesta, "N.° 00001")
        self.assertContains(respuesta, "No válido como comprobante de pago")
        self.assertContains(respuesta, "window.print()")

    def test_lista_excluye_anuladas_de_los_totales(self):
        servicios.registrar_venta(self.tienda, self.tienda.usuario, [LineaPedida(self.producto.pk, 1)])
        anulada = servicios.registrar_venta(self.tienda, self.tienda.usuario, [LineaPedida(self.producto.pk, 2)])
        servicios.anular_venta(anulada, self.tienda.usuario, "Error de digitación")
        respuesta = self.client.get(reverse("inventario:ventas"))
        self.assertEqual(respuesta.context["resumen"]["total"], Decimal("700.00"))
        self.assertEqual(respuesta.context["resumen"]["cantidad"], 1)
        self.assertEqual(respuesta.context["resumen"]["unidades"], 1)
        self.assertContains(respuesta, "Anulada")

    def test_anular_desde_la_pagina(self):
        venta = servicios.registrar_venta(self.tienda, self.tienda.usuario, [LineaPedida(self.producto.pk, 2)])
        url = reverse("inventario:venta_anular", args=[venta.pk])
        respuesta = self.client.post(url, {"motivo": "abc"})  # motivo muy corto
        self.assertEqual(respuesta.status_code, 200)
        self.client.post(url, {"motivo": "El cliente devolvió todo"})
        venta.refresh_from_db()
        self.producto.refresh_from_db()
        self.assertTrue(venta.anulada)
        self.assertEqual(self.producto.stock, 5)

    def test_otra_tienda_no_ve_mis_ventas(self):
        venta = servicios.registrar_venta(self.tienda, self.tienda.usuario, [LineaPedida(self.producto.pk, 1)])
        self.client.force_login(self.otra_tienda.usuario)
        for nombre in ("inventario:venta_detalle", "inventario:venta_anular"):
            self.assertEqual(self.client.get(reverse(nombre, args=[venta.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("inventario:ventas")).context["resumen"]["cantidad"], 0)

    def test_pestana_ventas_en_mis_productos(self):
        respuesta = self.client.get(reverse("catalogo:mis_productos"))
        self.assertContains(respuesta, f'href="{reverse("inventario:ventas")}"')
