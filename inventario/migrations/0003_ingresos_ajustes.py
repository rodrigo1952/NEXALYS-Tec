"""
Etapa 3 del inventario: ingresos numerados y anulables, y ajustes con dos tipos de devolución.

- Ingreso: número correlativo por tienda (como las ventas) y datos de anulación.
- Movimiento: nuevo tipo "Ingreso anulado"; la devolución se separa en
  "de un cliente" (suma stock) y "al proveedor" (resta stock).
"""

from django.db import migrations, models


def numerar_ingresos(apps, schema_editor):
    """Si ya hubiera ingresos (por ejemplo, creados desde el admin), se numeran por tienda en orden de fecha."""
    Ingreso = apps.get_model("inventario", "Ingreso")
    contadores = {}
    for ingreso in Ingreso.objects.order_by("fecha", "id"):
        contadores[ingreso.tienda_id] = contadores.get(ingreso.tienda_id, 0) + 1
        ingreso.numero = contadores[ingreso.tienda_id]
        ingreso.save(update_fields=["numero"])


def separar_devoluciones(apps, schema_editor):
    Movimiento = apps.get_model("inventario", "Movimiento")
    Movimiento.objects.filter(motivo="devolucion").update(motivo="devolucion_cliente")


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0002_inventario_inicial"),
    ]

    operations = [
        migrations.AddField(
            model_name="ingreso",
            name="numero",
            field=models.PositiveIntegerField(default=0, verbose_name="número de ingreso"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="ingreso",
            name="anulado",
            field=models.BooleanField(default=False, verbose_name="anulado"),
        ),
        migrations.AddField(
            model_name="ingreso",
            name="motivo_anulacion",
            field=models.CharField(blank=True, max_length=255, verbose_name="motivo de la anulación"),
        ),
        migrations.AddField(
            model_name="ingreso",
            name="anulado_en",
            field=models.DateTimeField(blank=True, null=True, verbose_name="anulado el"),
        ),
        migrations.RunPython(numerar_ingresos, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="ingreso",
            constraint=models.UniqueConstraint(fields=("tienda", "numero"), name="numero_de_ingreso_unico_por_tienda"),
        ),
        migrations.AlterField(
            model_name="movimiento",
            name="tipo",
            field=models.CharField(
                choices=[("inicial", "Inventario inicial"), ("venta", "Venta"), ("anulacion", "Venta anulada"),
                         ("ingreso", "Ingreso de mercadería"), ("ingreso_anulado", "Ingreso anulado"),
                         ("ajuste", "Ajuste"), ("conteo", "Conteo físico"),
                         ("edicion", "Cambio al editar el producto")],
                max_length=20, verbose_name="tipo",
            ),
        ),
        migrations.AlterField(
            model_name="movimiento",
            name="motivo",
            field=models.CharField(
                blank=True,
                choices=[("dano", "Producto dañado"), ("perdida", "Pérdida o robo"),
                         ("devolucion_cliente", "Devolución de un cliente"),
                         ("devolucion_proveedor", "Devolución al proveedor"), ("otro", "Otro")],
                max_length=25, verbose_name="motivo",
            ),
        ),
        migrations.RunPython(separar_devoluciones, migrations.RunPython.noop),
    ]
