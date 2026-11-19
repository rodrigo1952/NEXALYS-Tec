# Escaneos del código QR de cada tienda (tiendas/qr.py): solo la tienda y la fecha.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tiendas", "0009_servicios_y_lema"),
    ]

    operations = [
        migrations.CreateModel(
            name="EscaneoQR",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="fecha")),
                (
                    "tienda",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="escaneos_qr",
                        to="tiendas.tienda",
                        verbose_name="tienda",
                    ),
                ),
            ],
            options={
                "verbose_name": "escaneo del QR",
                "verbose_name_plural": "escaneos del QR",
                "ordering": ["-fecha"],
            },
        ),
    ]
