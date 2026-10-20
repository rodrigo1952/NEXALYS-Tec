"""
Orden de Inicio:
  - destacado_desde: fecha en que la tienda marcó el producto como destacado.
    A los que ya eran destacados se les pone su última modificación.
  - VistaProducto: una vista por visitante al día, para ordenar por popularidad.
"""

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models
from django.db.models import F


def llenar_destacado_desde(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    Producto.objects.filter(destacado=True, destacado_desde__isnull=True).update(destacado_desde=F("actualizado"))


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0006_relevancia_busqueda"),
    ]

    operations = [
        migrations.AddField(
            model_name="producto",
            name="destacado_desde",
            field=models.DateTimeField(blank=True, editable=False, null=True, verbose_name="destacado desde"),
        ),
        migrations.RunPython(llenar_destacado_desde, migrations.RunPython.noop),
        migrations.CreateModel(
            name="VistaProducto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("visitante", models.CharField(max_length=64, verbose_name="visitante")),
                ("fecha", models.DateField(default=django.utils.timezone.localdate, verbose_name="fecha")),
                (
                    "producto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="vistas", to="catalogo.producto"
                    ),
                ),
            ],
            options={
                "verbose_name": "vista de producto",
                "verbose_name_plural": "vistas de productos",
                "indexes": [models.Index(fields=["producto", "fecha"], name="vista_producto_fecha")],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("producto", "visitante", "fecha"), name="una_vista_por_visitante_al_dia"
                    )
                ],
            },
        ),
    ]
