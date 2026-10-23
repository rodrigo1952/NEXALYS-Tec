"""
Los pedidos guardan el nombre de la tienda y del producto, y la tienda puede quedar
vacía: así, si una tienda se elimina automáticamente, sus ventas se conservan anónimas.
"""

import django.db.models.deletion
from django.db import migrations, models


def copiar_nombres(apps, schema_editor):
    Pedido = apps.get_model("pedidos", "Pedido")
    for pedido in Pedido.objects.select_related("tienda", "producto"):
        Pedido.objects.filter(pk=pedido.pk).update(
            tienda_nombre=pedido.tienda.nombre, producto_nombre=pedido.producto.nombre
        )


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0001_initial"),
        ("tiendas", "0006_suspendida_en"),
        ("catalogo", "0008_imagenes_por_tienda"),
    ]

    operations = [
        migrations.AddField(
            model_name="pedido",
            name="tienda_nombre",
            field=models.CharField(blank=True, max_length=100, verbose_name="tienda (nombre)"),
        ),
        migrations.AddField(
            model_name="pedido",
            name="producto_nombre",
            field=models.CharField(blank=True, max_length=200, verbose_name="producto (nombre)"),
        ),
        migrations.AlterField(
            model_name="pedido",
            name="tienda",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="pedidos", to="tiendas.tienda", verbose_name="tienda",
            ),
        ),
        migrations.AlterField(
            model_name="pedido",
            name="producto",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="pedidos", to="catalogo.producto", verbose_name="producto",
            ),
        ),
        migrations.RunPython(copiar_nombres, migrations.RunPython.noop),
    ]
