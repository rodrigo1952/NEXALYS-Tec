"""
Reglas de negocio de las ventas (y luego ingresos y ajustes).

Cada operación es atómica: si algo falla, no se guarda nada a medias.

Control de concurrencia (dos vendedores o dos pestañas al mismo tiempo):
  1. Se bloquean las filas que se van a cambiar (select_for_update). En SQLite el
     bloqueo lo da transaction_mode="IMMEDIATE" (config/settings.py).
  2. Los productos se bloquean siempre en el mismo orden (por id), para que dos
     ventas con los mismos productos no se esperen la una a la otra para siempre.
  3. El stock se vuelve a leer DENTRO de la transacción: nunca queda negativo.
  4. El número de venta se calcula con la tienda bloqueada: no se repite.
"""

from collections import OrderedDict
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from catalogo.models import Producto
from tiendas.models import Tienda

from .kardex import Tipo, registrar
from .models import FichaInventario, LineaVenta, Venta


class StockInsuficiente(Exception):
    def __init__(self, producto, disponible, pedido):
        self.producto, self.disponible, self.pedido = producto, disponible, pedido
        super().__init__(
            f"No hay stock suficiente de \"{producto}\": pediste {pedido} y quedan {disponible}."
        )


class OperacionNoPermitida(Exception):
    pass


@dataclass
class LineaPedida:
    producto_id: int
    cantidad: int
    precio: Decimal | None = None  # None = precio actual del producto (con oferta)


def numero_venta(venta):
    return f"{venta.numero:05d}"


@transaction.atomic
def registrar_venta(tienda, usuario, lineas, *, metodo_pago=Venta.MetodoPago.EFECTIVO,
                    cliente_nombre="", cliente_documento="", nota=""):
    """Registra una venta con una o varias líneas y descuenta el stock. Devuelve la venta."""
    if not lineas:
        raise OperacionNoPermitida("Agrega al menos un producto a la venta.")
    tienda = Tienda.objects.select_for_update().get(pk=tienda.pk)  # serializa el número de venta

    # Cantidad total por producto (por si el mismo producto aparece en dos líneas).
    por_producto = OrderedDict()
    for linea in lineas:
        por_producto[linea.producto_id] = por_producto.get(linea.producto_id, 0) + linea.cantidad

    productos = {
        p.pk: p
        for p in Producto.objects.select_for_update().filter(tienda=tienda, pk__in=sorted(por_producto)).order_by("pk")
    }
    if len(productos) != len(por_producto):
        raise OperacionNoPermitida("Uno de los productos ya no existe o no es de tu tienda.")
    for producto_id, cantidad in por_producto.items():
        producto = productos[producto_id]
        if producto.stock < cantidad:
            raise StockInsuficiente(producto.nombre, producto.stock, cantidad)

    costos = dict(FichaInventario.objects.filter(producto_id__in=productos).values_list("producto_id", "costo"))
    numero = (Venta.objects.filter(tienda=tienda).aggregate(m=Max("numero"))["m"] or 0) + 1
    venta = Venta.objects.create(
        tienda=tienda, tienda_nombre=tienda.nombre, numero=numero, usuario=usuario,
        metodo_pago=metodo_pago, cliente_nombre=cliente_nombre.strip(),
        cliente_documento=cliente_documento.strip(), nota=nota.strip(),
    )
    total = Decimal("0")
    for linea in lineas:
        producto = productos[linea.producto_id]
        precio = producto.precio_final if linea.precio is None else linea.precio
        LineaVenta.objects.create(
            venta=venta, producto=producto, producto_nombre=producto.nombre,
            cantidad=linea.cantidad, precio_unitario=precio, costo_unitario=costos.get(producto.pk),
        )
        total += precio * linea.cantidad
        producto.stock -= linea.cantidad
        # "actualizado" también: así quien edita el producto en otra pestaña se entera del cambio.
        producto.save(update_fields=["stock", "actualizado"])
        registrar(producto, Tipo.VENTA, -linea.cantidad, usuario=usuario, venta=venta,
                  nota=f"Venta N.° {numero_venta(venta)}")
    venta.total = total
    venta.save(update_fields=["total"])
    return venta


@transaction.atomic
def anular_venta(venta, usuario, motivo):
    """Anula una venta registrada por error: el stock vuelve y queda en el kardex."""
    try:
        venta = Venta.objects.select_for_update().get(pk=venta.pk)
    except Venta.DoesNotExist:
        raise OperacionNoPermitida("Esta venta ya no existe.")
    if venta.anulada:
        raise OperacionNoPermitida("Esta venta ya estaba anulada (quizá otra persona la anuló hace un momento).")
    lineas = list(venta.lineas.all())
    ids = sorted({l.producto_id for l in lineas if l.producto_id})
    productos = {p.pk: p for p in Producto.objects.select_for_update().filter(pk__in=ids).order_by("pk")}
    for linea in lineas:
        producto = productos.get(linea.producto_id)
        if producto is None:
            continue  # el producto se eliminó: no hay stock que devolver
        producto.stock += linea.cantidad
        producto.save(update_fields=["stock", "actualizado"])
        registrar(producto, Tipo.ANULACION, linea.cantidad, usuario=usuario, venta=venta,
                  nota=f"Anulación de la venta N.° {numero_venta(venta)}: {motivo}")
    venta.anulada = True
    venta.motivo_anulacion = motivo.strip()
    venta.anulada_en = timezone.now()
    venta.save(update_fields=["anulada", "motivo_anulacion", "anulada_en"])
    return venta
