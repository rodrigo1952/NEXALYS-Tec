import decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

import catalogo.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("tiendas", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Categoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=60, unique=True, verbose_name="nombre")),
                ("activa", models.BooleanField(default=True, verbose_name="activa")),
            ],
            options={
                "verbose_name": "categoría",
                "verbose_name_plural": "categorías",
                "ordering": ["nombre"],
            },
        ),
        migrations.CreateModel(
            name="Marca",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=60, unique=True, verbose_name="nombre")),
                ("activa", models.BooleanField(default=True, verbose_name="activa")),
            ],
            options={
                "verbose_name": "marca",
                "verbose_name_plural": "marcas",
                "ordering": ["nombre"],
            },
        ),
        migrations.CreateModel(
            name="Producto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=150, verbose_name="nombre")),
                ("descripcion", models.TextField(blank=True, verbose_name="descripción")),
                (
                    "precio",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=8,
                        validators=[
                            django.core.validators.MinValueValidator(
                                decimal.Decimal("0.10"),
                                message="El precio debe ser de al menos S/ 0.10.",
                            )
                        ],
                        verbose_name="precio (S/)",
                    ),
                ),
                ("stock", models.PositiveIntegerField(default=0, verbose_name="stock")),
                (
                    "imagen",
                    models.ImageField(
                        blank=True,
                        help_text="Opcional. JPG, PNG o WEBP de máximo 2 MB.",
                        upload_to="productos/",
                        validators=[
                            django.core.validators.FileExtensionValidator(
                                allowed_extensions=["jpg", "jpeg", "png", "webp"]
                            ),
                            catalogo.models.validar_tamano_imagen,
                        ],
                        verbose_name="imagen",
                    ),
                ),
                (
                    "activo",
                    models.BooleanField(
                        default=True,
                        help_text="Desmárcalo para ocultar el producto del catálogo sin eliminarlo.",
                        verbose_name="publicado",
                    ),
                ),
                ("creado", models.DateTimeField(auto_now_add=True, verbose_name="creado")),
                ("actualizado", models.DateTimeField(auto_now=True, verbose_name="actualizado")),
                (
                    "categoria",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="productos",
                        to="catalogo.categoria",
                        verbose_name="categoría",
                    ),
                ),
                (
                    "marca",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="productos",
                        to="catalogo.marca",
                        verbose_name="marca",
                    ),
                ),
                (
                    "tienda",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="productos",
                        to="tiendas.tienda",
                        verbose_name="tienda",
                    ),
                ),
            ],
            options={
                "verbose_name": "producto",
                "verbose_name_plural": "productos",
                "ordering": ["-creado"],
                "constraints": [
                    models.UniqueConstraint(fields=("tienda", "nombre"), name="producto_unico_por_tienda"),
                ],
            },
        ),
    ]
