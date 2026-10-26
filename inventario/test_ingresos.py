"""Inventario · Etapa 3: ingresos de mercadería, ajustes y conteo físico."""

from decimal import Decimal

from django.urls import reverse

from catalogo.tests import BaseCatalogo

from . import servicios
from .models import FichaInventario, Ingreso, Movimiento, Proveedor
from .servicios import Contado, LineaPedida, LineaRecibida


def datos_ingreso(lineas, **extra):
    datos = {
        "lineas-TOTAL_FORMS": "10", "lineas-INITIAL_FORMS": "0",
        "lineas-MIN_NUM_FORMS": "0", "lineas-MAX_NUM_FORMS": "10",
        "proveedor": "", "documento": "", "nota": "",
    }
    for i, (producto, cantidad, costo) in enumerate(lineas):
        datos[f"lineas-{i}-producto"] = str(producto.pk)
        datos[f"lineas-{i}-cantidad"] = str(cantidad)
        datos[f"lineas-{i}-costo"] = "" if costo is None else str(costo)
    datos.update(extra)
    return datos


class CostoPromedioTests(BaseCatalogo):
    def test_formula(self):
        self.assertEqual(servicios.costo_promedio(2, Decimal("100"), 3, Decimal("120")), Decimal("112.00"))
        self.assertEqual(servicios.costo_promedio(0, Decimal("100"), 3, Decimal("120")), Decimal("120"))
        self.assertEqual(servicios.costo_promedio(5, None, 3, Decimal("120")), Decimal("120"))

    def test_quitar_del_promedio_es_lo_contrario(self):
        self.assertEqual(servicios.quitar_del_promedio(5, Decimal("112.00"), 3, Decimal("120")), Decimal("100.00"))
        self.assertEqual(servicios.quitar_del_promedio(3, Decimal("120"), 3, Decimal("120")), Decimal("120"))


class IngresosTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.producto = self.crear_producto(nombre="Galaxy A15", stock=2)
        FichaInventario.objects.create(producto=self.producto, costo=Decimal("100.00"))
        self.proveedor = Proveedor.objects.create(tienda=self.tienda, nombre="Distribuidora Cusco")

    def recibir(self, *lineas, **extra):
        return servicios.registrar_ingreso(self.tienda, self.tienda.usuario, [LineaRecibida(*l) for l in lineas], **extra)

    def test_ingreso_suma_stock_actualiza_costo_y_kardex(self):
        ingreso = self.recibir((self.producto.pk, 3, Decimal("120.00")), proveedor=self.proveedor, documento="F001-12")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 5)
        self.assertEqual(FichaInventario.objects.get(producto=self.producto).costo, Decimal("112.00"))
        self.assertEqual((ingreso.numero, ingreso.total, ingreso.proveedor_nombre), (1, Decimal("360.00"), "Distribuidora Cusco"))
        movimiento = Movimiento.objects.get(tipo=Movimiento.Tipo.INGRESO, ingreso=ingreso)
        self.assertEqual((movimiento.cantidad, movimiento.stock_resultante), (3, 5))
        self.assertIn("Distribuidora Cusco", movimiento.nota)

    def test_producto_sin_ficha_toma_el_costo_del_ingreso(self):
        nuevo = self.crear_producto(nombre="Funda", stock=0)
        self.recibir((nuevo.pk, 10, Decimal("8.50")))
        self.assertEqual(FichaInventario.objects.get(producto=nuevo).costo, Decimal("8.50"))

    def test_numeracion_por_tienda(self):
        self.assertEqual(self.recibir((self.producto.pk, 1, Decimal("100"))).numero, 1)
        self.assertEqual(self.recibir((self.producto.pk, 1, Decimal("100"))).numero, 2)
        otro = self.crear_producto(tienda=self.otra_tienda, nombre="Mouse", stock=0)
        ingreso = servicios.registrar_ingreso(self.otra_tienda, self.otra_tienda.usuario, [LineaRecibida(otro.pk, 1, Decimal("5"))])
        self.assertEqual(ingreso.numero, 1)

    def test_no_acepta_productos_ni_proveedores_de_otra_tienda(self):
        ajeno = self.crear_producto(tienda=self.otra_tienda, nombre="Ajeno")
        with self.assertRaises(servicios.OperacionNoPermitida):
            self.recibir((ajeno.pk, 1, Decimal("5")))
        proveedor_ajeno = Proveedor.objects.create(tienda=self.otra_tienda, nombre="Otro")
        with self.assertRaises(servicios.OperacionNoPermitida):
            self.recibir((self.producto.pk, 1, Decimal("5")), proveedor=proveedor_ajeno)
        self.assertEqual(Ingreso.objects.count(), 0)

    def test_anular_resta_stock_y_restaura_el_costo(self):
        ingreso = self.recibir((self.producto.pk, 3, Decimal("120.00")))
        servicios.anular_ingreso(ingreso, self.tienda.usuario, "Se registró dos veces")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 2)
        self.assertEqual(FichaInventario.objects.get(producto=self.producto).costo, Decimal("100.00"))
        ingreso.refresh_from_db()
        self.assertTrue(ingreso.anulado)
        self.assertEqual(Movimiento.objects.get(tipo=Movimiento.Tipo.INGRESO_ANULADO).cantidad, -3)
        with self.assertRaises(servicios.OperacionNoPermitida):
            servicios.anular_ingreso(ingreso, self.tienda.usuario, "Otra vez")

    def test_no_se_anula_si_ya_se_vendio_parte(self):
        ingreso = self.recibir((self.producto.pk, 3, Decimal("120.00")))
        servicios.registrar_venta(self.tienda, self.tienda.usuario, [LineaPedida(self.producto.pk, 4)])
        with self.assertRaises(servicios.OperacionNoPermitida):
            servicios.anular_ingreso(ingreso, self.tienda.usuario, "Error de digitación")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 1)

    def test_formulario_registra_el_ingreso(self):
        self.client.force_login(self.tienda.usuario)
        datos = datos_ingreso([(self.producto, 4, "110.00")], proveedor=str(self.proveedor.pk), documento="G001-5")
        respuesta = self.client.post(reverse("inventario:ingreso_nuevo"), datos)
        ingreso = Ingreso.objects.get()
        self.assertRedirects(respuesta, reverse("inventario:ingreso_detalle", args=[ingreso.pk]))
        self.assertEqual((ingreso.documento, ingreso.total), ("G001-5", Decimal("440.00")))

    def test_formulario_exige_el_costo(self):
        self.client.force_login(self.tienda.usuario)
        respuesta = self.client.post(reverse("inventario:ingreso_nuevo"), datos_ingreso([(self.producto, 4, None)]))
        self.assertContains(respuesta, "Indica cuánto pagaste por unidad")
        self.assertEqual(Ingreso.objects.count(), 0)

    def test_formulario_sugiere_el_costo_de_la_ficha(self):
        self.client.force_login(self.tienda.usuario)
        respuesta = self.client.get(reverse("inventario:ingreso_nuevo"))
        self.assertContains(respuesta, 'data-costo="100.00"')

    def test_lista_y_detalle_privados(self):
        ingreso = self.recibir((self.producto.pk, 1, Decimal("100")))
        self.client.force_login(self.tienda.usuario)
        self.assertContains(self.client.get(reverse("inventario:ingresos")), "00001")
        self.client.force_login(self.otra_tienda.usuario)
        for nombre in ("inventario:ingreso_detalle", "inventario:ingreso_anular"):
            self.assertEqual(self.client.get(reverse(nombre, args=[ingreso.pk])).status_code, 404)

    def test_kardex_enlaza_al_ingreso(self):
        ingreso = self.recibir((self.producto.pk, 1, Decimal("100")))
        self.client.force_login(self.tienda.usuario)
        respuesta = self.client.get(reverse("inventario:kardex", args=[self.producto.pk]))
        self.assertContains(respuesta, reverse("inventario:ingreso_detalle", args=[ingreso.pk]))


class AjustesTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.producto = self.crear_producto(nombre="Galaxy A15", stock=5)
        self.client.force_login(self.tienda.usuario)
        self.url = reverse("inventario:ajuste_nuevo")

    def ajustar(self, motivo, cantidad, nota=""):
        return self.client.post(self.url, {"producto": self.producto.pk, "motivo": motivo, "cantidad": cantidad, "nota": nota})

    def stock(self):
        self.producto.refresh_from_db()
        return self.producto.stock

    def test_danado_resta(self):
        self.assertRedirects(self.ajustar("dano", 2, "Pantalla rota"), reverse("inventario:ajustes"))
        self.assertEqual(self.stock(), 3)
        ajuste = Movimiento.objects.get(tipo=Movimiento.Tipo.AJUSTE)
        self.assertEqual((ajuste.motivo, ajuste.cantidad, ajuste.stock_resultante), ("dano", -2, 3))

    def test_devoluciones(self):
        self.ajustar("devolucion_cliente", 1)
        self.assertEqual(self.stock(), 6)
        self.ajustar("devolucion_proveedor", 4)
        self.assertEqual(self.stock(), 2)

    def test_otro_motivo_exige_detalle_y_puede_sumar_o_restar(self):
        respuesta = self.ajustar("otro_suma", 1)
        self.assertContains(respuesta, "Explica el motivo")
        self.ajustar("otro_suma", 2, "Encontrado en el almacén")
        self.ajustar("otro_resta", 1, "Muestra para vitrina")
        self.assertEqual(self.stock(), 6)
        self.assertEqual(Movimiento.objects.filter(motivo="otro").count(), 2)

    def test_no_deja_el_stock_negativo(self):
        respuesta = self.ajustar("perdida", 9)
        self.assertContains(respuesta, "No hay stock suficiente")
        self.assertEqual(self.stock(), 5)

    def test_motivo_y_signo_deben_coincidir(self):
        with self.assertRaises(servicios.OperacionNoPermitida):
            servicios.registrar_ajuste(self.tienda, None, self.producto.pk, "dano", 2)

    def test_otra_tienda_no_ajusta_mis_productos(self):
        self.client.force_login(self.otra_tienda.usuario)
        self.ajustar("dano", 1)
        self.assertEqual(self.stock(), 5)

    def test_lista_de_ajustes(self):
        self.ajustar("dano", 1)
        respuesta = self.client.get(reverse("inventario:ajustes"))
        self.assertContains(respuesta, "Producto dañado")


class ConteoTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.a = self.crear_producto(nombre="Galaxy A15", stock=5)
        self.b = self.crear_producto(nombre="Funda", stock=10)
        self.c = self.crear_producto(nombre="Cargador", stock=3)
        self.client.force_login(self.tienda.usuario)
        self.url = reverse("inventario:conteo")

    def test_corrige_solo_los_que_tienen_diferencia(self):
        datos = {f"contado_{self.a.pk}": "4", f"visto_{self.a.pk}": "5",
                 f"contado_{self.b.pk}": "10", f"visto_{self.b.pk}": "10",
                 f"contado_{self.c.pk}": "", f"visto_{self.c.pk}": "3"}
        respuesta = self.client.post(self.url, datos)
        self.assertRedirects(respuesta, f"{reverse('inventario:ajustes')}?tipo=conteo")
        for p in (self.a, self.b, self.c):
            p.refresh_from_db()
        self.assertEqual((self.a.stock, self.b.stock, self.c.stock), (4, 10, 3))
        conteo = Movimiento.objects.get(tipo=Movimiento.Tipo.CONTEO)
        self.assertEqual((conteo.producto, conteo.cantidad), (self.a, -1))

    def test_si_el_stock_cambio_mientras_contaba_no_se_corrige(self):
        servicios.registrar_venta(self.tienda, self.tienda.usuario, [LineaPedida(self.a.pk, 1)])  # ahora 4
        resultado = servicios.registrar_conteo(self.tienda, None, [Contado(self.a.pk, 5, 5)])
        self.assertEqual(resultado.cambiaron, ["Galaxy A15"])
        self.a.refresh_from_db()
        self.assertEqual(self.a.stock, 4)

    def test_valores_invalidos(self):
        respuesta = self.client.post(self.url, {f"contado_{self.a.pk}": "-2", f"visto_{self.a.pk}": "5"})
        self.assertContains(respuesta, "Escribe un número entero")
        self.a.refresh_from_db()
        self.assertEqual(self.a.stock, 5)

    def test_no_toca_productos_de_otra_tienda(self):
        ajeno = self.crear_producto(tienda=self.otra_tienda, nombre="Ajeno", stock=7)
        self.client.post(self.url, {f"contado_{ajeno.pk}": "0", f"visto_{ajeno.pk}": "7"})
        ajeno.refresh_from_db()
        self.assertEqual(ajeno.stock, 7)

    def test_la_lista_solo_muestra_mis_productos(self):
        self.crear_producto(tienda=self.otra_tienda, nombre="Producto ajeno")
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, "Galaxy A15")
        self.assertNotContains(respuesta, "Producto ajeno")

    def test_pestanas(self):
        respuesta = self.client.get(reverse("catalogo:mis_productos"))
        for nombre in ("inventario:ingresos", "inventario:ajustes"):
            self.assertContains(respuesta, f'href="{reverse(nombre)}"')
