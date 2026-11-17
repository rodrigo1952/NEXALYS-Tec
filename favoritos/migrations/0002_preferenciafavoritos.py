"""
Orden preferido de «Mis favoritos» de cada cliente.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("favoritos", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PreferenciaFavoritos",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("orden", models.CharField(choices=[("recomendado", "Recomendado"), ("recientes", "Agregados recientemente"), ("nombre", "Nombre (A-Z)"), ("precio_asc", "Precio: menor a mayor"), ("precio_desc", "Precio: mayor a menor"), ("descuento", "Mayor descuento")], default="recomendado", max_length=20, verbose_name="ordenar por")),
                ("usuario", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="preferencia_favoritos", to=settings.AUTH_USER_MODEL, verbose_name="cliente")),
            ],
            options={
                "verbose_name": "preferencia de favoritos",
                "verbose_name_plural": "preferencias de favoritos",
            },
        ),
    ]
