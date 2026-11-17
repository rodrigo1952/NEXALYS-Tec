"""
Fecha en que un producto agotado volvió a tener stock (para ordenar «Mis favoritos»).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0010_categoria_icono"),
    ]

    operations = [
        migrations.AddField(
            model_name="producto",
            name="repuesto_el",
            field=models.DateTimeField(blank=True, editable=False, null=True, verbose_name="volvió a tener stock el"),
        ),
    ]
