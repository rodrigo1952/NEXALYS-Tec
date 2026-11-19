# Visitas que llegan escaneando el QR de la página (administracion/qr.py).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("administracion", "0006_responder_reclamo"),
    ]

    operations = [
        migrations.CreateModel(
            name="VisitaQR",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="fecha")),
            ],
            options={
                "verbose_name": "visita por el QR",
                "verbose_name_plural": "visitas por el QR",
                "ordering": ["-fecha"],
            },
        ),
    ]
