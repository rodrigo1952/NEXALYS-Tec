"""
Reglas de negocio de los pedidos que afectan el stock.

Cada operación es atómica: si algo falla, no se guarda ningún cambio a medias.

Control de concurrencia: dos personas (o dos pestañas) pueden actuar sobre el
mismo pedido o producto al mismo tiempo. Por eso cada operación:
  1. Bloquea las filas que va a cambiar (select_for_update). En SQLite el
     bloqueo lo da transaction_mode="IMMEDIATE" (ver config/settings.py).
  2. Vuelve a leer el estado y el stock DENTRO de la transacción, en vez de
     confiar en el objeto que la vista leyó antes, que puede estar desactualizado.
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


def _bloquear_pedido(pedido):
    """Lee el pedido actual de la base de datos (no el de la vista) y lo bloquea."""
    try:
        return Pedido.objects.select_for_update().get(pk=pedido.pk)
    except Pedido.DoesNotExist:
        raise OperacionNoPermitida("Este pedido ya no existe: otra persona lo eliminó hace un momento.")


def _guardar_stock(producto):
    # "actualizado" también se guarda: así la tienda que está editando el producto
    # en otra pestaña se entera de que el stock cambió (ver ProductoForm).
    producto.save(update_fields=["stock", "actualizado"])


@transaction.atomic
def registrar_pedido(pedido):
    """Guarda un pedido nuevo, toma el precio actual del producto y descuenta el stock."""
    producto = _bloquear(pedido.producto_id)
    if producto.stock < pedido.cantidad:
        raise StockInsuficiente(producto.stock)
    producto.stock -= pedido.cantidad
    _guardar_stock(producto)
    pedido.precio_unitario = producto.precio
    pedido.estado = Pedido.Estado.PENDIENTE
    pedido.save()
    return pedido


@transaction.atomic
def actualizar_pedido(pedido, producto_anterior_id, cantidad_anterior):
    """Edita un pedido pendiente: devuelve el stock anterior y descuenta el nuevo."""
    actual = _bloquear_pedido(pedido)
    if actual.estado != Pedido.Estado.PENDIENTE:
        raise OperacionNoPermitida("Solo se pueden editar pedidos pendientes.")
    # Se usan los valores guardados en la base de datos, no los que tenía el formulario.
    producto_anterior_id, cantidad_anterior = actual.producto_id, actual.cantidad

    anterior = _bloquear(producto_anterior_id)
    anterior.stock += cantidad_anterior
    _guardar_stock(anterior)

    nuevo = _bloquear(pedido.producto_id)  # si es el mismo producto, ya tiene el stock devuelto
    if nuevo.stock < pedido.cantidad:
        raise StockInsuficiente(nuevo.stock)  # la transacción deshace la devolución anterior
    nuevo.stock -= pedido.cantidad
    _guardar_stock(nuevo)

    if pedido.producto_id != producto_anterior_id:
        pedido.precio_unitario = nuevo.precio
    pedido.estado = actual.estado
    pedido.save()
    return pedido


@transaction.atomic
def cambiar_estado(pedido, nuevo_estado):
    actual = _bloquear_pedido(pedido)
    if not actual.puede_cambiar_a(nuevo_estado):
        raise OperacionNoPermitida(
            f"Un pedido {actual.get_estado_display().lower()} no puede pasar a ese estado. "
            "Puede que otra persona lo haya cambiado hace un momento."
        )
    if nuevo_estado == Pedido.Estado.CANCELADO:
        producto = _bloquear(actual.producto_id)
        producto.stock += actual.cantidad  # al cancelar se restituye el stock
        _guardar_stock(producto)
    actual.estado = nuevo_estado
    actual.save(update_fields=["estado", "actualizado"])
    pedido.estado = actual.estado  # la vista muestra el estado nuevo
    return actual


@transaction.atomic
def eliminar_pedido(pedido):
    actual = _bloquear_pedido(pedido)
    if not actual.eliminable:
        raise OperacionNoPermitida(
            "Los pedidos confirmados o entregados no se eliminan: forman parte del historial de ventas."
        )
    if actual.estado == Pedido.Estado.PENDIENTE:
        producto = _bloquear(actual.producto_id)
        producto.stock += actual.cantidad
        _guardar_stock(producto)
    actual.delete()
