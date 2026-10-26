"""
Etapa 5: los pedidos se convierten en ventas (migración inventario 0004) y la tabla de
pedidos se elimina (pedidos 0003). Se prueba la migración de verdad: se vuelve a la
base de datos de antes, se crean pedidos y se migra hacia adelante.
"""

from datetime import timedelta
from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

ANTES = [("inventario", "0003_ingresos_ajustes"), ("pedidos", "0002_conservar_ventas_anonimas")]
DESPUES = [("inventario", "0004_convertir_pedidos"), ("pedidos", "0003_retirar_pedidos")]


class ConvertirPedidosTests(TransactionTestCase):
    serialized_rollback = True  # así las demás pruebas conservan los datos iniciales (roles, categorías)

    def migrar(self, destino):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(destino)
        return executor.loader.project_state(destino).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_conversion(self):
        apps = self.migrar(ANTES)
        User = apps.get_model("auth", "User")
        Tienda = apps.get_model("tiendas", "Tienda")
        Categoria = apps.get_model("catalogo", "Categoria")
        Marca = apps.get_model("catalogo", "Marca")
        Producto = apps.get_model("catalogo", "Producto")
        Pedido = apps.get_model("pedidos", "Pedido")
        Venta = apps.get_model("inventario", "Venta")
        Movimiento = apps.get_model("inventario", "Movimiento")
        FichaInventario = apps.get_model("inventario", "FichaInventario")

        usuario = User.objects.create(username="tienda1", email="t1@ejemplo.com")
        tienda = Tienda.objects.create(usuario=usuario, nombre="Tienda Uno", direccion="Jr. Lima 100",
                                       whatsapp="911111111", estado="activa")
        categoria, _ = Categoria.objects.get_or_create(nombre="Celulares")
        marca, _ = Marca.objects.get_or_create(nombre="Samsung")
        producto = Producto.objects.create(tienda=tienda, categoria=categoria, marca=marca, nombre="Galaxy A15",
                                           precio=Decimal("700.00"), stock=3)
        FichaInventario.objects.create(producto=producto, costo=Decimal("550.00"))
        # La tienda ya tenía una venta registrada: los pedidos se numeran después.
        Venta.objects.create(tienda=tienda, tienda_nombre="Tienda Uno", numero=1, total=Decimal("700.00"))

        def pedido(estado, dias, **extra):
            p = Pedido.objects.create(
                tienda=tienda, tienda_nombre="Tienda Uno", producto=producto, producto_nombre="Galaxy A15",
                cliente_nombre="Ana Quispe", cliente_telefono="987654321", cantidad=2,
                precio_unitario=Decimal("690.00"), estado=estado, **extra,
            )
            Pedido.objects.filter(pk=p.pk).update(creado=timezone.now() - timedelta(days=dias))
            Movimiento.objects.create(tienda=tienda, tienda_nombre="Tienda Uno", producto=producto,
                                      producto_nombre="Galaxy A15", tipo="venta", cantidad=-2,
                                      stock_resultante=1, nota=f"Pedido #{p.pk}")
            return p

        entregado = pedido("entregado", 10, observacion="Entrega en el local")
        pendiente = pedido("pendiente", 5)
        pedido("cancelado", 3)
        anonimo = Pedido.objects.create(
            tienda=None, tienda_nombre="Tienda eliminada", producto=None, producto_nombre="Mouse",
            cliente_nombre="Cliente anónimo", cliente_telefono="", cantidad=1,
            precio_unitario=Decimal("50.00"), estado="entregado",
        )

        apps = self.migrar(DESPUES)
        Venta = apps.get_model("inventario", "Venta")
        Movimiento = apps.get_model("inventario", "Movimiento")

        convertidas = Venta.objects.exclude(origen="").order_by("fecha")
        self.assertEqual(convertidas.count(), 3)  # el cancelado no se convierte
        primera = Venta.objects.get(origen=f"Pedido #{entregado.pk} (entregado)")
        self.assertEqual((primera.numero, primera.total, primera.metodo_pago), (2, Decimal("1380.00"), "otro"))
        self.assertEqual(primera.cliente_nombre, "Ana Quispe")
        self.assertIn("Cel. 987654321", primera.nota)
        self.assertIn("Entrega en el local", primera.nota)
        linea = primera.lineas.get()
        self.assertEqual((linea.cantidad, linea.precio_unitario, linea.costo_unitario),
                         (2, Decimal("690.00"), Decimal("550.00")))
        self.assertEqual(Venta.objects.get(origen=f"Pedido #{pendiente.pk} (pendiente)").numero, 3)
        # El kardex del pedido queda enlazado a su venta.
        self.assertEqual(Movimiento.objects.get(nota=f"Pedido #{entregado.pk}").venta_id, primera.pk)
        # Las ventas de tiendas eliminadas siguen anónimas.
        anonima = Venta.objects.get(origen=f"Pedido #{anonimo.pk} (entregado)")
        self.assertIsNone(anonima.tienda_id)
        self.assertEqual(anonima.tienda_nombre, "Tienda eliminada")
        # El stock no se vuelve a descontar.
        self.assertEqual(apps.get_model("catalogo", "Producto").objects.get(pk=producto.pk).stock, 3)
        # La tabla de pedidos ya no existe.
        self.assertNotIn("pedidos_pedido", connection.introspection.table_names())
