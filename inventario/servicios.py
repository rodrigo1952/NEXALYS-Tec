"""
Reglas de negocio del inventario: ventas, ingresos, ajustes y conteo físico.

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

from .kardex import Motivo, Tipo, registrar
from .models import FichaInventario, Ingreso, LineaIngreso, LineaVenta, Venta


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


@dataclass
class LineaRecibida:
    producto_id: int
    cantidad: int
    costo: Decimal


def numero_venta(venta):
    return f"{venta.numero:05d}"


def numero_ingreso(ingreso):
    return f"{ingreso.numero:05d}"


def _bloquear_productos(tienda, ids):
    """Bloquea los productos de la tienda siempre en el mismo orden (por id). Devuelve {id: producto}."""
    return {
        p.pk: p
        for p in Producto.objects.select_for_update().filter(tienda=tienda, pk__in=sorted(set(ids))).order_by("pk")
    }


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


# ---------------------------------------------------------------------------
# Ingresos de mercadería (Etapa 3)
# ---------------------------------------------------------------------------

CENTIMO = Decimal("0.01")


def costo_promedio(stock_antes, costo_antes, cantidad, costo_nuevo):
    """
    Costo promedio ponderado. Ej.: tenías 2 a S/ 100 y entran 3 a S/ 120:
    (2 × 100 + 3 × 120) / 5 = S/ 112.00
    Si no había stock o no tenía costo, queda el costo nuevo.
    """
    if costo_antes is None or stock_antes <= 0:
        return costo_nuevo
    valor = stock_antes * costo_antes + cantidad * costo_nuevo
    return (valor / (stock_antes + cantidad)).quantize(CENTIMO)


def quitar_del_promedio(stock_actual, costo_actual, cantidad, costo_quitado):
    """Lo contrario de costo_promedio: al anular un ingreso, su costo sale del promedio."""
    restante = stock_actual - cantidad
    if costo_actual is None or restante <= 0:
        return costo_actual
    valor = stock_actual * costo_actual - cantidad * costo_quitado
    if valor <= 0:
        return costo_actual
    return (valor / restante).quantize(CENTIMO)


@transaction.atomic
def registrar_ingreso(tienda, usuario, lineas, *, proveedor=None, documento="", nota=""):
    """Registra mercadería recibida: suma stock, actualiza el costo promedio y anota en el kardex."""
    if not lineas:
        raise OperacionNoPermitida("Agrega al menos un producto al ingreso.")
    tienda = Tienda.objects.select_for_update().get(pk=tienda.pk)
    productos = _bloquear_productos(tienda, [l.producto_id for l in lineas])
    if len(productos) != len({l.producto_id for l in lineas}):
        raise OperacionNoPermitida("Uno de los productos ya no existe o no es de tu tienda.")
    if proveedor is not None and proveedor.tienda_id != tienda.pk:
        raise OperacionNoPermitida("Ese proveedor no es de tu tienda.")

    numero = (Ingreso.objects.filter(tienda=tienda).aggregate(m=Max("numero"))["m"] or 0) + 1
    ingreso = Ingreso.objects.create(
        tienda=tienda, numero=numero, usuario=usuario, proveedor=proveedor,
        proveedor_nombre=proveedor.nombre if proveedor else "",
        documento=documento.strip(), nota=nota.strip(),
    )
    detalle = f"Ingreso N.° {numero_ingreso(ingreso)}" + (f" · {proveedor.nombre}" if proveedor else "")
    total = Decimal("0")
    for linea in lineas:
        producto = productos[linea.producto_id]
        LineaIngreso.objects.create(
            ingreso=ingreso, producto=producto, producto_nombre=producto.nombre,
            cantidad=linea.cantidad, costo_unitario=linea.costo,
        )
        total += linea.costo * linea.cantidad
        ficha, _ = FichaInventario.objects.get_or_create(producto=producto)
        ficha.costo = costo_promedio(producto.stock, ficha.costo, linea.cantidad, linea.costo)
        ficha.save(update_fields=["costo", "actualizado"])
        producto.stock += linea.cantidad
        producto.save(update_fields=["stock", "actualizado"])
        registrar(producto, Tipo.INGRESO, linea.cantidad, usuario=usuario, ingreso=ingreso, nota=detalle)
    ingreso.total = total
    ingreso.save(update_fields=["total"])
    return ingreso


@transaction.atomic
def anular_ingreso(ingreso, usuario, motivo):
    """Anula un ingreso registrado por error: el stock que entró se resta y su costo sale del promedio."""
    try:
        ingreso = Ingreso.objects.select_for_update().get(pk=ingreso.pk)
    except Ingreso.DoesNotExist:
        raise OperacionNoPermitida("Este ingreso ya no existe.")
    if ingreso.anulado:
        raise OperacionNoPermitida("Este ingreso ya estaba anulado (quizá otra persona lo anuló hace un momento).")
    lineas = list(ingreso.lineas.all())
    productos = _bloquear_productos(ingreso.tienda, [l.producto_id for l in lineas if l.producto_id])

    por_producto = {}
    for linea in lineas:
        if linea.producto_id in productos:
            por_producto[linea.producto_id] = por_producto.get(linea.producto_id, 0) + linea.cantidad
    for producto_id, cantidad in por_producto.items():
        producto = productos[producto_id]
        if producto.stock < cantidad:
            raise OperacionNoPermitida(
                f"No se puede anular: de \"{producto.nombre}\" entraron {cantidad} y ahora solo quedan "
                f"{producto.stock} (ya vendiste o ajustaste parte). Corrige la diferencia con un ajuste."
            )

    nota = f"Anulación del ingreso N.° {numero_ingreso(ingreso)}: {motivo.strip()}"
    for linea in lineas:
        producto = productos.get(linea.producto_id)
        if producto is None:
            continue  # el producto se eliminó: no hay stock que restar
        ficha = FichaInventario.objects.filter(producto=producto).first()
        if ficha is not None:
            ficha.costo = quitar_del_promedio(producto.stock, ficha.costo, linea.cantidad, linea.costo_unitario)
            ficha.save(update_fields=["costo", "actualizado"])
        producto.stock -= linea.cantidad
        producto.save(update_fields=["stock", "actualizado"])
        registrar(producto, Tipo.INGRESO_ANULADO, -linea.cantidad, usuario=usuario, ingreso=ingreso, nota=nota)
    ingreso.anulado = True
    ingreso.motivo_anulacion = motivo.strip()
    ingreso.anulado_en = timezone.now()
    ingreso.save(update_fields=["anulado", "motivo_anulacion", "anulado_en"])
    return ingreso


# ---------------------------------------------------------------------------
# Ajustes y conteo físico (Etapa 3)
# ---------------------------------------------------------------------------

# Motivos que restan stock; la devolución de un cliente suma. "Otro" puede sumar o restar.
MOTIVOS_QUE_RESTAN = {Motivo.DANO.value, Motivo.PERDIDA.value, Motivo.DEVOLUCION_PROVEEDOR.value}


@transaction.atomic
def registrar_ajuste(tienda, usuario, producto_id, motivo, cantidad, nota=""):
    """
    Ajuste de stock por daño, pérdida, devolución u otro motivo.
    cantidad lleva signo: positiva suma, negativa resta.
    """
    if not cantidad:
        raise OperacionNoPermitida("La cantidad no puede ser cero.")
    if motivo in MOTIVOS_QUE_RESTAN and cantidad > 0 or motivo == Motivo.DEVOLUCION_CLIENTE and cantidad < 0:
        raise OperacionNoPermitida("La cantidad no corresponde con el motivo.")
    productos = _bloquear_productos(tienda, [producto_id])
    if not productos:
        raise OperacionNoPermitida("Ese producto ya no existe o no es de tu tienda.")
    producto = productos[producto_id]
    if producto.stock + cantidad < 0:
        raise StockInsuficiente(producto.nombre, producto.stock, -cantidad)
    producto.stock += cantidad
    producto.save(update_fields=["stock", "actualizado"])
    return registrar(producto, Tipo.AJUSTE, cantidad, usuario=usuario, motivo=motivo, nota=nota.strip())


@dataclass
class Contado:
    producto_id: int
    contado: int  # lo que se contó en el local
    visto: int    # el stock que mostraba la página al empezar a contar


@dataclass
class ResultadoConteo:
    corregidos: list
    sin_diferencia: int
    cambiaron: list  # nombres de productos cuyo stock cambió mientras se contaba


@transaction.atomic
def registrar_conteo(tienda, usuario, conteos, nota=""):
    """
    Corrige el stock con lo contado en el local. Solo se anotan los productos con diferencia.

    Si mientras se contaba hubo una venta u otro movimiento (el stock ya no es el que
    mostraba la página), ese producto NO se corrige: hay que volver a contarlo. Así un
    conteo viejo no borra una venta recién hecha.
    """
    productos = _bloquear_productos(tienda, [c.producto_id for c in conteos])
    resultado = ResultadoConteo([], 0, [])
    for conteo in conteos:
        producto = productos.get(conteo.producto_id)
        if producto is None:
            continue  # se eliminó mientras se contaba
        if producto.stock != conteo.visto:
            resultado.cambiaron.append(producto.nombre)
            continue
        diferencia = conteo.contado - producto.stock
        if diferencia == 0:
            resultado.sin_diferencia += 1
            continue
        detalle = f"Conteo físico: el sistema tenía {producto.stock} y se contaron {conteo.contado}"
        producto.stock = conteo.contado
        producto.save(update_fields=["stock", "actualizado"])
        registrar(producto, Tipo.CONTEO, diferencia, usuario=usuario,
                  nota=f"{detalle}. {nota.strip()}" if nota.strip() else detalle)
        resultado.corregidos.append(producto.nombre)
    return resultado
