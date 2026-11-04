"""Ubicación del local en el mapa (opcional): para «Tiendas cercanas» y «Cómo llegar»."""

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tiendas", "0006_suspendida_en"),
    ]

    operations = [
        migrations.AddField(
            model_name="tienda",
            name="latitud",
            field=models.DecimalField(
                blank=True, decimal_places=6, max_digits=9, null=True, verbose_name="latitud",
                validators=[django.core.validators.MinValueValidator(-90), django.core.validators.MaxValueValidator(90)],
            ),
        ),
        migrations.AddField(
            model_name="tienda",
            name="longitud",
            field=models.DecimalField(
                blank=True, decimal_places=6, max_digits=9, null=True, verbose_name="longitud",
                validators=[django.core.validators.MinValueValidator(-180), django.core.validators.MaxValueValidator(180)],
            ),
        ),
    ]
