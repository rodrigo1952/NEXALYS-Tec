"""
Pruebas del CRUD de pedidos (CU-08) y sus reglas de stock.
Ejecutar con:  python manage.py test
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Marca, Producto
from tiendas.tests import crear_tienda

from .models import Pedido


class BasePedidos(TestCase):
    def setUp(self):
        self.tienda = crear_tienda("tienda1", "Tienda Uno", "911111111")
        self.otra_tienda = crear_tienda("tienda2", "Tienda Dos", "922222222")
        categoria = Categoria.objects.get(nombre="Celulares")
        marca = Marca.objects.get(nombre="Samsung")
        self.producto = Producto.objects.create(
            tienda=self.tienda, categoria=categoria, marca=marca,
            nombre="Galaxy A15", precio=Decimal("700.00"), stock=10,
        )
        self.otro_producto = Producto.objects.create(
            tienda=self.tienda, categoria=categoria, marca=marca,
            nombre="Galaxy A25", precio=Decimal("900.00"), stock=3,
        )
        self.producto_ajeno = Producto.objects.create(
            tienda=self.otra_tienda, categoria=categoria, marca=marca,
            nombre="Galaxy ajeno", precio=Decimal("500.00"), stock=5,
        )
        self.client.force_login(self.tienda.usuario)

    def datos(self, **cambios):
        datos = {
            "producto": self.producto.pk,
            "cantidad": "2",
            "cliente_nombre": "Ana Quispe",
            "cliente_telefono": "987654321",
            "observacion": "",
        }
        datos.update(cambios)
        return datos

    def crear_pedido(self, cantidad=2, estado=Pedido.Estado.PENDIENTE, producto=None, tienda=None):
        producto = producto or self.producto
        producto.stock -= cantidad
        producto.save()
        return Pedido.objects.create(
            tienda=tienda or self.tienda, producto=producto, cantidad=cantidad,
            precio_unitario=producto.precio, cliente_nombre="Luis Mamani",
            cliente_telefono="955555555", estado=estado,
        )

    def stock(self, producto):
        producto.refresh_from_db()
        return producto.stock


class RegistrarPedidoTests(BasePedidos):
    def test_registrar_pedido_descuenta_stock_y_toma_el_precio(self):
        self.client.post(reverse("pedidos:crear"), self.datos(cantidad="3"))
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.estado, Pedido.Estado.PENDIENTE)
        self.assertEqual(pedido.precio_unitario, Decimal("700.00"))
        self.assertEqual(pedido.total, Decimal("2100.00"))
        self.assertEqual(self.stock(self.producto), 7)

    def test_stock_insuficiente_no_registra_el_pedido(self):
        respuesta = self.client.post(reverse("pedidos:crear"), self.datos(cantidad="11"))
        self.assertIn("cantidad", respuesta.context["form"].errors)
        self.assertFalse(Pedido.objects.exists())
        self.assertEqual(self.stock(self.producto), 10)

    def test_cantidad_cero_se_rechaza(self):
        respuesta = self.client.post(reverse("pedidos:crear"), self.datos(cantidad="0"))
        self.assertIn("cantidad", respuesta.context["form"].errors)

    def test_celular_invalido_se_rechaza(self):
        respuesta = self.client.post(reverse("pedidos:crear"), self.datos(cliente_telefono="12345"))
        self.assertIn("cliente_telefono", respuesta.context["form"].errors)

    def test_no_puede_usar_producto_de_otra_tienda(self):
        respuesta = self.client.post(reverse("pedidos:crear"), self.datos(producto=self.producto_ajeno.pk))
        self.assertIn("producto", respuesta.context["form"].errors)
        self.assertEqual(self.stock(self.producto_ajeno), 5)

    def test_producto_agotado_no_aparece_para_nuevos_pedidos(self):
        self.otro_producto.stock = 0
        self.otro_producto.save()
        respuesta = self.client.get(reverse("pedidos:crear"))
        self.assertNotContains(respuesta, "Galaxy A25")


class EditarPedidoTests(BasePedidos):
    def test_editar_cantidad_ajusta_el_stock(self):
        pedido = self.crear_pedido(cantidad=2)  # stock queda en 8
        self.client.post(reverse("pedidos:editar", args=[pedido.pk]), self.datos(cantidad="5"))
        self.assertEqual(self.stock(self.producto), 5)

    def test_cambiar_de_producto_devuelve_y_descuenta(self):
        pedido = self.crear_pedido(cantidad=2)  # producto: 8
        self.client.post(
            reverse("pedidos:editar", args=[pedido.pk]),
            self.datos(producto=self.otro_producto.pk, cantidad="1"),
        )
        pedido.refresh_from_db()
        self.assertEqual(self.stock(self.producto), 10)
        self.assertEqual(self.stock(self.otro_producto), 2)
        self.assertEqual(pedido.precio_unitario, Decimal("900.00"))

    def test_editar_puede_usar_las_unidades_ya_reservadas(self):
        pedido = self.crear_pedido(cantidad=10)  # stock queda en 0
        respuesta = self.client.post(reverse("pedidos:editar", args=[pedido.pk]), self.datos(cantidad="10"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.stock(self.producto), 0)

    def test_no_se_edita_un_pedido_confirmado(self):
        pedido = self.crear_pedido(estado=Pedido.Estado.CONFIRMADO)
        self.client.post(reverse("pedidos:editar", args=[pedido.pk]), self.datos(cantidad="1"))
        pedido.refresh_from_db()
        self.assertEqual(pedido.cantidad, 2)


class EstadoPedidoTests(BasePedidos):
    def cambiar(self, pedido, estado):
        self.client.post(reverse("pedidos:estado", args=[pedido.pk]), {"estado": estado})
        pedido.refresh_from_db()
        return pedido

    def test_flujo_completo_pendiente_confirmado_entregado(self):
        pedido = self.crear_pedido()
        self.assertEqual(self.cambiar(pedido, "confirmado").estado, "confirmado")
        self.assertEqual(self.cambiar(pedido, "entregado").estado, "entregado")

    def test_no_se_puede_saltar_de_pendiente_a_entregado(self):
        pedido = self.crear_pedido()
        self.assertEqual(self.cambiar(pedido, "entregado").estado, "pendiente")

    def test_un_pedido_entregado_no_cambia_mas(self):
        pedido = self.crear_pedido(estado=Pedido.Estado.ENTREGADO)
        self.assertEqual(self.cambiar(pedido, "cancelado").estado, "entregado")

    def test_cancelar_devuelve_el_stock(self):
        pedido = self.crear_pedido(cantidad=4)  # stock queda en 6
        self.cambiar(pedido, "cancelado")
        self.assertEqual(self.stock(self.producto), 10)


class EliminarPedidoTests(BasePedidos):
    def test_eliminar_pedido_pendiente_devuelve_el_stock(self):
        pedido = self.crear_pedido(cantidad=3)
        self.client.post(reverse("pedidos:eliminar", args=[pedido.pk]))
        self.assertFalse(Pedido.objects.filter(pk=pedido.pk).exists())
        self.assertEqual(self.stock(self.producto), 10)

    def test_no_se_elimina_un_pedido_entregado(self):
        pedido = self.crear_pedido(estado=Pedido.Estado.ENTREGADO)
        self.client.post(reverse("pedidos:eliminar", args=[pedido.pk]))
        self.assertTrue(Pedido.objects.filter(pk=pedido.pk).exists())

    def test_producto_con_pedidos_no_se_puede_eliminar(self):
        self.crear_pedido()
        self.client.post(reverse("catalogo:eliminar", args=[self.producto.pk]))
        self.assertTrue(Producto.objects.filter(pk=self.producto.pk).exists())


class PermisosPedidosTests(BasePedidos):
    def test_no_puede_ver_pedidos_de_otra_tienda(self):
        ajeno = self.crear_pedido(producto=self.producto_ajeno, tienda=self.otra_tienda)
        respuesta = self.client.get(reverse("pedidos:detalle", args=[ajeno.pk]))
        self.assertEqual(respuesta.status_code, 404)

    def test_listado_muestra_solo_pedidos_propios(self):
        self.crear_pedido()
        self.crear_pedido(producto=self.producto_ajeno, tienda=self.otra_tienda)
        respuesta = self.client.get(reverse("pedidos:lista"))
        self.assertEqual(respuesta.context["pagina"].paginator.count, 1)

    def test_cliente_no_accede_a_pedidos(self):
        cliente = User.objects.create_user("cliente1", "c@ejemplo.com", "ClaveSegura#2026")
        self.client.force_login(cliente)
        respuesta = self.client.get(reverse("pedidos:lista"))
        self.assertEqual(respuesta.status_code, 403)

    def test_resumen_de_ventas_cuenta_solo_entregados(self):
        self.crear_pedido(cantidad=2, estado=Pedido.Estado.ENTREGADO)
        self.crear_pedido(cantidad=1, estado=Pedido.Estado.PENDIENTE)
        respuesta = self.client.get(reverse("pedidos:lista"))
        self.assertEqual(respuesta.context["resumen"]["num_pedidos"], 1)
        self.assertEqual(respuesta.context["resumen"]["ventas"], Decimal("1400.00"))
