"""
Fecha en que un producto oculto volvió a verse en el catálogo (para «Mis favoritos»).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0011_producto_repuesto_el"),
    ]

    operations = [
        migrations.AddField(
            model_name="producto",
            name="republicado_el",
            field=models.DateTimeField(blank=True, editable=False, null=True, verbose_name="volvió a estar disponible el"),
        ),
    ]
