"""Etapa 1: las imágenes nuevas se guardan en una carpeta por tienda (ver catalogo/archivos.py)."""

import django.core.validators
from django.db import migrations, models

import catalogo.archivos
import catalogo.models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0007_vistas_y_destacado_desde"),
    ]

    operations = [
        migrations.AlterField(
            model_name="producto",
            name="imagen",
            field=models.ImageField(
                blank=True,
                help_text="Opcional. JPG, PNG o WEBP de máximo 2 MB.",
                upload_to=catalogo.archivos.ruta_imagen_producto,
                validators=[
                    django.core.validators.FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
                    catalogo.models.validar_tamano_imagen,
                ],
                verbose_name="imagen",
            ),
        ),
        migrations.AlterField(
            model_name="fotoproducto",
            name="imagen",
            field=models.ImageField(
                upload_to=catalogo.archivos.ruta_foto_producto,
                validators=[
                    django.core.validators.FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
                    catalogo.models.validar_tamano_imagen,
                ],
                verbose_name="imagen",
            ),
        ),
    ]
