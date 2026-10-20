"""Etapa 1: el logo se guarda en la carpeta de su tienda (ver catalogo/archivos.py)."""

import django.core.validators
from django.db import migrations, models

import catalogo.archivos
import catalogo.models


class Migration(migrations.Migration):

    dependencies = [
        ("tiendas", "0004_motivo_suspension"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tienda",
            name="logo",
            field=models.ImageField(
                blank=True,
                help_text="Opcional. JPG, PNG o WEBP de máximo 2 MB. Se recomienda una imagen cuadrada.",
                upload_to=catalogo.archivos.ruta_logo_tienda,
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=["jpg", "jpeg", "png", "webp"]
                    ),
                    catalogo.models.validar_tamano_imagen,
                ],
                verbose_name="logo",
            ),
        ),
    ]
