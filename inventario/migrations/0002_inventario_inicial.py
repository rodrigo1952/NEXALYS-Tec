"""
El stock que cada producto tiene hoy queda como su "Inventario inicial" en el kardex
(con la fecha de hoy, cuando empieza el inventario). Así no empieza en blanco.
"""

from django.db import migrations


def crear_inventario_inicial(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    Movimiento = apps.get_model("inventario", "Movimiento")
    for producto in Producto.objects.select_related("tienda").filter(stock__gt=0):
        if not Movimiento.objects.filter(producto=producto).exists():
            Movimiento.objects.create(
                tienda=producto.tienda, tienda_nombre=producto.tienda.nombre,
                producto=producto, producto_nombre=producto.nombre,
                tipo="inicial", cantidad=producto.stock, stock_resultante=producto.stock,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(crear_inventario_inicial, migrations.RunPython.noop),
    ]
