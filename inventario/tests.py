"""Inventario · Etapa 1: kardex automático, fichas de inventario y proveedores."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.urls import reverse

from catalogo.tests import BaseCatalogo

from .models import FichaInventario, Movimiento, Proveedor


class KardexAutomaticoTests(BaseCatalogo):
    def test_producto_nuevo_queda_como_inventario_inicial(self):
        self.client.force_login(self.tienda.usuario)
        self.client.post(reverse("catalogo:crear"), self.datos_formulario(stock="10"))
        movimiento = Movimiento.objects.get()
        self.assertEqual((movimiento.tipo, movimiento.cantidad, movimiento.stock_resultante), ("inicial", 10, 10))
        self.assertEqual(movimiento.usuario, self.tienda.usuario)

    def test_los_datos_de_la_ficha_estan_en_el_formulario_de_productos(self):
        # La Ficha se retiró: precio de compra, stock mínimo y código se editan en el formulario del producto.
        self.client.force_login(self.tienda.usuario)
        campos = self.client.get(reverse("catalogo:crear")).context["form"].fields
        for campo in ("precio_compra", "stock_minimo", "codigo"):
            self.assertIn(campo, campos)

    def test_cambiar_el_stock_al_editar_queda_anotado(self):
        producto = self.crear_producto(nombre="Galaxy A25", stock=10)
        self.client.force_login(self.tienda.usuario)
        datos = self.datos_formulario(stock="7", version=producto.actualizado.isoformat())
        self.client.post(reverse("catalogo:editar", args=[producto.pk]), datos)
        cambio = Movimiento.objects.get(tipo=Movimiento.Tipo.EDICION)
        self.assertEqual((cambio.cantidad, cambio.stock_resultante), (-3, 7))
        self.assertEqual(cambio.usuario, self.tienda.usuario)

    def test_guardar_sin_cambiar_el_stock_no_anota_nada(self):
        producto = self.crear_producto(stock=5)
        producto.precio = Decimal("650.00")
        producto.save()
        self.assertEqual(Movimiento.objects.count(), 1)  # solo el inventario inicial

    def test_la_historia_se_conserva_si_se_elimina_el_producto(self):
        producto = self.crear_producto(nombre="Producto viejo", stock=4)
        producto.delete()
        movimiento = Movimiento.objects.get()
        self.assertIsNone(movimiento.producto)
        self.assertEqual(movimiento.producto_nombre, "Producto viejo")


class SeccionInventarioTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.producto = self.crear_producto(nombre="Galaxy A15", stock=4)
        self.client.force_login(self.tienda.usuario)

    def test_inventario_vive_dentro_de_mis_productos(self):
        # Una sola entrada en el menú: "Mis productos" (catálogo + inventario).
        menu = self.client.get(reverse("inicio"))
        self.assertContains(menu, f'href="{reverse("catalogo:mis_productos")}"')
        self.assertNotContains(menu, f'href="{reverse("inventario:inicio")}"')
        self.assertRedirects(self.client.get(reverse("inventario:inicio")), reverse("catalogo:mis_productos"))
        # Desde la ficha o el kardex, "Mis productos" sigue marcado en el menú.
        kardex = self.client.get(reverse("inventario:kardex", args=[self.producto.pk]))
        self.assertContains(kardex, f'active" aria-current="page" href="{reverse("catalogo:mis_productos")}"')

    def test_mis_productos_muestra_valor_y_alertas(self):
        FichaInventario.objects.create(producto=self.producto, costo=Decimal("500.00"), stock_minimo=5)
        self.crear_producto(nombre="Agotado", stock=0)
        respuesta = self.client.get(reverse("catalogo:mis_productos"))
        resumen = respuesta.context["resumen"]
        self.assertEqual(resumen["valor"], Decimal("2000.00"))  # 4 × 500
        self.assertEqual(resumen["stock_bajo"], 1)
        self.assertEqual(resumen["agotados"], 1)
        self.assertContains(respuesta, "Stock bajo")
        self.assertContains(respuesta, "Agotado")
        self.assertNotContains(respuesta, reverse("inventario:ficha", args=[self.producto.pk]))  # ya no hay Ficha
        self.assertContains(respuesta, reverse("inventario:kardex", args=[self.producto.pk]))
        # Filtros rápidos en vez de tarjetas.
        self.assertContains(respuesta, "filtro-rapido")
        self.assertContains(respuesta, "?ver=agotados")

    def test_filtros_rapidos(self):
        FichaInventario.objects.create(producto=self.producto, stock_minimo=5)  # 4 de stock: bajo
        self.crear_producto(nombre="Agotado", stock=0)
        url = reverse("catalogo:mis_productos")
        self.assertEqual([p.nombre for p in self.client.get(url, {"ver": "bajo"}).context["pagina"]], ["Galaxy A15"])
        self.assertEqual([p.nombre for p in self.client.get(url, {"ver": "agotados"}).context["pagina"]], ["Agotado"])

    def test_filtro_de_alertas(self):
        FichaInventario.objects.create(producto=self.producto, stock_minimo=5)  # 4 de stock: bajo
        self.crear_producto(nombre="Con stock de sobra", stock=50)
        respuesta = self.client.get(reverse("catalogo:mis_productos"), {"alerta": "1"})
        self.assertEqual([p.nombre for p in respuesta.context["pagina"]], ["Galaxy A15"])

    def editar_producto(self, **cambios):
        datos = self.datos_formulario(nombre="Galaxy A15", stock="4", version=self.producto.actualizado.isoformat())
        datos.update(cambios)
        return self.client.post(reverse("catalogo:editar", args=[self.producto.pk]), datos)

    def test_la_ficha_se_edita_en_el_formulario_del_producto(self):
        self.editar_producto(precio_compra="480.50", stock_minimo="2", codigo="CEL-001")
        ficha = FichaInventario.objects.get(producto=self.producto)
        self.assertEqual((ficha.costo, ficha.stock_minimo, ficha.codigo), (Decimal("480.50"), 2, "CEL-001"))
        # La dirección antigua de la ficha lleva al formulario del producto.
        self.assertRedirects(self.client.get(reverse("inventario:ficha", args=[self.producto.pk])),
                             reverse("catalogo:editar", args=[self.producto.pk]))

    def test_codigo_no_se_repite_en_la_misma_tienda(self):
        otro = self.crear_producto(nombre="Galaxy A25")
        FichaInventario.objects.create(producto=otro, codigo="CEL-001")
        respuesta = self.editar_producto(codigo="cel-001")
        self.assertIn("codigo", respuesta.context["form"].errors)

    def test_kardex_del_producto(self):
        respuesta = self.client.get(reverse("inventario:kardex", args=[self.producto.pk]))
        self.assertContains(respuesta, "Inventario inicial")
        self.assertContains(respuesta, "+4")

    def test_no_ve_productos_de_otra_tienda(self):
        ajeno = self.crear_producto(tienda=self.otra_tienda, nombre="Ajeno")
        self.assertEqual(self.client.get(reverse("inventario:ficha", args=[ajeno.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("inventario:kardex", args=[ajeno.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("catalogo:mis_productos")), "Ajeno")

    def test_el_costo_es_privado(self):
        FichaInventario.objects.create(producto=self.producto, costo=Decimal("543.21"))
        self.client.logout()
        self.assertNotContains(self.client.get(reverse("catalogo:detalle", args=[self.producto.pk])), "543")
        self.client.force_login(User.objects.create_superuser("admin", "a@ejemplo.com", "ClaveSegura#2026"))
        self.assertNotContains(self.client.get(reverse("administracion:productos")), "543")
        self.assertEqual(self.client.get(reverse("inventario:productos")).status_code, 403)

    def test_un_cliente_no_entra(self):
        cliente = User.objects.create_user("cliente9", "c9@ejemplo.com", "ClaveSegura#2026")
        self.client.force_login(cliente)
        self.assertEqual(self.client.get(reverse("inventario:productos")).status_code, 403)


class ProveedoresTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.tienda.usuario)

    def test_crear_editar_y_eliminar(self):
        self.client.post(reverse("inventario:proveedor_crear"), {"nombre": "Distribuidora Cusco", "ruc": "20123456789"})
        proveedor = Proveedor.objects.get()
        self.assertEqual(proveedor.tienda, self.tienda)
        self.client.post(reverse("inventario:proveedor_editar", args=[proveedor.pk]), {"nombre": "Distribuidora Cusco SAC"})
        proveedor.refresh_from_db()
        self.assertEqual(proveedor.nombre, "Distribuidora Cusco SAC")
        self.client.post(reverse("inventario:proveedor_eliminar", args=[proveedor.pk]))
        self.assertFalse(Proveedor.objects.exists())

    def test_ruc_invalido_y_nombre_repetido(self):
        Proveedor.objects.create(tienda=self.tienda, nombre="Tecno Lima")
        respuesta = self.client.post(reverse("inventario:proveedor_crear"), {"nombre": "tecno lima", "ruc": "123"})
        errores = respuesta.context["form"].errors
        self.assertIn("nombre", errores)
        self.assertIn("ruc", errores)

    def test_otra_tienda_puede_tener_el_mismo_proveedor(self):
        Proveedor.objects.create(tienda=self.otra_tienda, nombre="Tecno Lima")
        self.client.post(reverse("inventario:proveedor_crear"), {"nombre": "Tecno Lima"})
        self.assertEqual(Proveedor.objects.filter(tienda=self.tienda).count(), 1)

    def test_no_ve_proveedores_de_otra_tienda(self):
        ajeno = Proveedor.objects.create(tienda=self.otra_tienda, nombre="Proveedor ajeno")
        self.assertNotContains(self.client.get(reverse("inventario:proveedores")), "Proveedor ajeno")
        self.assertEqual(self.client.get(reverse("inventario:proveedor_editar", args=[ajeno.pk])).status_code, 404)
