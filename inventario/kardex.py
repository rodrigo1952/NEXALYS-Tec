"""
Registrar líneas del kardex.

registrar() se llama DESPUÉS de cambiar el stock del producto y dentro de la misma
transacción (con el producto bloqueado si hay riesgo de acciones simultáneas). Así
el "stock después" de cada movimiento siempre coincide con el stock real.
"""

from .models import FichaInventario, Movimiento

Tipo = Movimiento.Tipo
Motivo = Movimiento.Motivo


def registrar(producto, tipo, cantidad, *, usuario=None, motivo="", venta=None, ingreso=None, nota="", fecha=None):
    if not cantidad:
        return None
    datos = {
        "tienda_id": producto.tienda_id,
        "tienda_nombre": producto.tienda.nombre,
        "producto": producto,
        "producto_nombre": producto.nombre,
        "tipo": tipo,
        "motivo": motivo,
        "cantidad": cantidad,
        "stock_resultante": producto.stock,
        "venta": venta,
        "ingreso": ingreso,
        "nota": nota[:255],
        "usuario": usuario if usuario is not None and getattr(usuario, "is_authenticated", False) else None,
    }
    if fecha is not None:
        datos["fecha"] = fecha
    return Movimiento.objects.create(**datos)


def ficha_de(producto):
    """La ficha de inventario del producto (se crea vacía la primera vez)."""
    ficha, _ = FichaInventario.objects.get_or_create(producto=producto)
    return ficha
