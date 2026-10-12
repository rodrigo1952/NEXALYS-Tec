"""
Reglas de negocio de los pedidos que afectan el stock.
Cada operación es atómica: si algo falla, no se guarda ningún cambio a medias.
"""

from django.db import transaction

from catalogo.models import Producto

from .models import Pedido


class StockInsuficiente(Exception):
    def __init__(self, disponible):
        self.disponible = disponible
        super().__init__(f"Solo hay {disponible} unidad(es) disponibles.")


class OperacionNoPermitida(Exception):
    pass


def _bloquear(producto_id):
    return Producto.objects.select_for_update().get(pk=producto_id)


@transaction.atomic
def registrar_pedido(pedido):
    """Guarda un pedido nuevo, toma el precio actual del producto y descuenta el stock."""
    producto = _bloquear(pedido.producto_id)
    if producto.stock < pedido.cantidad:
        raise StockInsuficiente(producto.stock)
    producto.stock -= pedido.cantidad
    producto.save(update_fields=["stock"])
    pedido.precio_unitario = producto.precio
    pedido.estado = Pedido.Estado.PENDIENTE
    pedido.save()
    return pedido


@transaction.atomic
def actualizar_pedido(pedido, producto_anterior_id, cantidad_anterior):
    """Edita un pedido pendiente: devuelve el stock anterior y descuenta el nuevo."""
    if Pedido.objects.get(pk=pedido.pk).estado != Pedido.Estado.PENDIENTE:
        raise OperacionNoPermitida("Solo se pueden editar pedidos pendientes.")

    anterior = _bloquear(producto_anterior_id)
    anterior.stock += cantidad_anterior
    anterior.save(update_fields=["stock"])

    nuevo = _bloquear(pedido.producto_id)  # si es el mismo producto, ya tiene el stock devuelto
    if nuevo.stock < pedido.cantidad:
        raise StockInsuficiente(nuevo.stock)  # la transacción deshace la devolución anterior
    nuevo.stock -= pedido.cantidad
    nuevo.save(update_fields=["stock"])

    if pedido.producto_id != producto_anterior_id:
        pedido.precio_unitario = nuevo.precio
    pedido.save()
    return pedido


@transaction.atomic
def cambiar_estado(pedido, nuevo_estado):
    if not pedido.puede_cambiar_a(nuevo_estado):
        raise OperacionNoPermitida(
            f"Un pedido {pedido.get_estado_display().lower()} no puede pasar a ese estado."
        )
    if nuevo_estado == Pedido.Estado.CANCELADO:
        producto = _bloquear(pedido.producto_id)
        producto.stock += pedido.cantidad  # al cancelar se restituye el stock
        producto.save(update_fields=["stock"])
    pedido.estado = nuevo_estado
    pedido.save(update_fields=["estado", "actualizado"])
    return pedido


@transaction.atomic
def eliminar_pedido(pedido):
    if not pedido.eliminable:
        raise OperacionNoPermitida(
            "Los pedidos confirmados o entregados no se eliminan: forman parte del historial de ventas."
        )
    if pedido.estado == Pedido.Estado.PENDIENTE:
        producto = _bloquear(pedido.producto_id)
        producto.stock += pedido.cantidad
        producto.save(update_fields=["stock"])
    pedido.delete()
