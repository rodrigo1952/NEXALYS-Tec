"""
Pruebas de escenarios concurrentes en pedidos.

Cómo se simula la concurrencia: dos peticiones "a la vez" significa que las dos
leyeron el pedido o el producto ANTES de que la otra guardara. En la prueba se
cargan dos copias del mismo registro (dos objetos desactualizados) y se usan una
después de la otra. Es exactamente el orden de lectura y escritura que produce
el problema, pero sin depender de la suerte con hilos.
"""

from django.conf import settings
from django.urls import reverse

from .models import Pedido
from .servicios import (
    OperacionNoPermitida,
    StockInsuficiente,
    actualizar_pedido,
    cambiar_estado,
    eliminar_pedido,
    registrar_pedido,
)
from .tests import BasePedidos


def nuevo_pedido(tienda, producto, cantidad):
    return Pedido(
        tienda=tienda, producto=producto, cantidad=cantidad,
        cliente_nombre="Ana Quispe", cliente_telefono="987654321",
    )


class ConcurrenciaPedidosTests(BasePedidos):
    def test_sqlite_usa_transacciones_immediate(self):
        # Sin esto, en SQLite el bloqueo de select_for_update no tiene efecto.
        self.assertEqual(settings.DATABASES["default"]["OPTIONS"]["transaction_mode"], "IMMEDIATE")

    def test_dos_pedidos_por_la_ultima_unidad(self):
        self.producto.stock = 1
        self.producto.save()
        # Las dos tiendas "vieron" 1 unidad disponible al mismo tiempo.
        primero = nuevo_pedido(self.tienda, self.producto, 1)
        segundo = nuevo_pedido(self.tienda, self.producto, 1)

        registrar_pedido(primero)
        with self.assertRaises(StockInsuficiente):
            registrar_pedido(segundo)

        self.assertEqual(self.stock(self.producto), 0)  # nunca negativo
        self.assertEqual(Pedido.objects.count(), 1)

    def test_cancelar_dos_veces_devuelve_el_stock_una_sola_vez(self):
        pedido = self.crear_pedido(cantidad=2)  # stock 10 -> 8
        copia_1 = Pedido.objects.get(pk=pedido.pk)  # p. ej. doble clic en "Cancelar"
        copia_2 = Pedido.objects.get(pk=pedido.pk)

        cambiar_estado(copia_1, Pedido.Estado.CANCELADO)
        with self.assertRaises(OperacionNoPermitida):
            cambiar_estado(copia_2, Pedido.Estado.CANCELADO)

        self.assertEqual(self.stock(self.producto), 10)  # antes de la corrección quedaba en 12

    def test_confirmar_y_cancelar_a_la_vez(self):
        pedido = self.crear_pedido(cantidad=2)
        para_confirmar = Pedido.objects.get(pk=pedido.pk)
        para_cancelar = Pedido.objects.get(pk=pedido.pk)

        cambiar_estado(para_cancelar, Pedido.Estado.CANCELADO)
        with self.assertRaises(OperacionNoPermitida):
            cambiar_estado(para_confirmar, Pedido.Estado.CONFIRMADO)

        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.CANCELADO)
        self.assertEqual(self.stock(self.producto), 10)

    def test_eliminar_pedido_que_otra_pestana_confirmo(self):
        pedido = self.crear_pedido(cantidad=2)
        para_eliminar = Pedido.objects.get(pk=pedido.pk)  # todavía dice "pendiente"

        cambiar_estado(Pedido.objects.get(pk=pedido.pk), Pedido.Estado.CONFIRMADO)
        with self.assertRaises(OperacionNoPermitida):
            eliminar_pedido(para_eliminar)

        self.assertTrue(Pedido.objects.filter(pk=pedido.pk).exists())  # el historial se conserva
        self.assertEqual(self.stock(self.producto), 8)  # no se devolvió stock

    def test_editar_pedido_que_otra_pestana_cancelo(self):
        pedido = self.crear_pedido(cantidad=2)
        para_editar = Pedido.objects.get(pk=pedido.pk)
        cambiar_estado(Pedido.objects.get(pk=pedido.pk), Pedido.Estado.CANCELADO)  # stock vuelve a 10

        para_editar.cantidad = 5
        with self.assertRaises(OperacionNoPermitida):
            actualizar_pedido(para_editar, self.producto.pk, 2)

        pedido.refresh_from_db()
        self.assertEqual(pedido.cantidad, 2)
        self.assertEqual(self.stock(self.producto), 10)

    def test_eliminar_pedido_ya_eliminado(self):
        pedido = self.crear_pedido(cantidad=2)
        copia = Pedido.objects.get(pk=pedido.pk)
        eliminar_pedido(pedido)  # stock 8 -> 10
        with self.assertRaises(OperacionNoPermitida):
            eliminar_pedido(copia)
        self.assertEqual(self.stock(self.producto), 10)  # no se devolvió dos veces

    def test_la_vista_muestra_un_aviso_en_vez_de_error(self):
        pedido = self.crear_pedido(cantidad=2)
        url = reverse("pedidos:estado", args=[pedido.pk])
        self.client.post(url, {"estado": Pedido.Estado.CANCELADO})
        respuesta = self.client.post(url, {"estado": Pedido.Estado.CANCELADO}, follow=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "no puede pasar a ese estado")
        self.assertEqual(self.stock(self.producto), 10)
