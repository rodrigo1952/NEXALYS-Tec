"""
Etapa 5: los pedidos se convierten en ventas.

- Pendientes, confirmados y entregados pasan a ventas (su stock ya estaba descontado:
  no se vuelve a descontar). Los cancelados no se convierten.
- Cada venta queda con origen "Pedido #12 (entregado)" y en la nota el celular del
  cliente y la observación. El método de pago queda como "Otro" (los pedidos no lo guardaban).
- El número de venta sigue después de las ventas que la tienda ya tenía.
- El costo de cada línea es el precio de compra actual del producto (los pedidos no
  guardaban el costo del momento); si no tiene, queda vacío y no cuenta en la ganancia.
- Las líneas del kardex de cada pedido quedan enlazadas a su nueva venta.
- Los pedidos de tiendas ya eliminadas se convierten en ventas anónimas ("Tienda eliminada").
"""

from django.db import migrations
from django.db.models import Max

ETIQUETAS = {"pendiente": "pendiente", "confirmado": "confirmado", "entregado": "entregado"}


def convertir(apps, schema_editor):
    Pedido = apps.get_model("pedidos", "Pedido")
    Venta = apps.get_model("inventario", "Venta")
    LineaVenta = apps.get_model("inventario", "LineaVenta")
    Movimiento = apps.get_model("inventario", "Movimiento")
    FichaInventario = apps.get_model("inventario", "FichaInventario")

    costos = dict(FichaInventario.objects.values_list("producto_id", "costo"))
    siguiente = {}
    pedidos = Pedido.objects.exclude(estado="cancelado").select_related("tienda").order_by("creado", "id")
    for pedido in pedidos:
        clave = pedido.tienda_id
        if clave not in siguiente:
            ultimo = Venta.objects.filter(tienda_id=clave).aggregate(m=Max("numero"))["m"] if clave else 0
            siguiente[clave] = (ultimo or 0) + 1
        numero = siguiente[clave]
        siguiente[clave] += 1

        partes = [f"Cel. {pedido.cliente_telefono}"] if pedido.cliente_telefono else []
        if pedido.observacion:
            partes.append(" ".join(pedido.observacion.split()))
        total = pedido.precio_unitario * pedido.cantidad
        venta = Venta.objects.create(
            tienda_id=pedido.tienda_id,
            tienda_nombre=(pedido.tienda.nombre if pedido.tienda_id else pedido.tienda_nombre) or "Tienda eliminada",
            numero=numero,
            fecha=pedido.creado,
            metodo_pago="otro",
            cliente_nombre=pedido.cliente_nombre[:120],
            total=total,
            nota=" · ".join(partes)[:255],
            origen=f"Pedido #{pedido.pk} ({ETIQUETAS.get(pedido.estado, pedido.estado)})",
            usuario_id=pedido.tienda.usuario_id if pedido.tienda_id else None,
        )
        LineaVenta.objects.create(
            venta=venta,
            producto_id=pedido.producto_id,
            producto_nombre=pedido.producto_nombre or "Producto eliminado",
            cantidad=pedido.cantidad,
            precio_unitario=pedido.precio_unitario,
            costo_unitario=costos.get(pedido.producto_id) if pedido.producto_id else None,
        )
        Movimiento.objects.filter(
            tipo="venta", venta__isnull=True,
            nota__in=[f"Pedido #{pedido.pk}", f"Pedido #{pedido.pk} editado"],
        ).update(venta=venta)


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0003_ingresos_ajustes"),
        ("pedidos", "0002_conservar_ventas_anonimas"),
    ]

    operations = [
        migrations.RunPython(convertir, migrations.RunPython.noop),
    ]
