"""
Ofertas, productos destacados, fotos adicionales y búsqueda sin tildes.
Al final llena el texto de búsqueda de los productos que ya existían.
"""

import decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

import catalogo.models
from catalogo.busqueda import normalizar


def llenar_texto_busqueda(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    for producto in Producto.objects.select_related("marca", "categoria"):
        texto = " ".join([producto.nombre, producto.descripcion, producto.marca.nombre, producto.categoria.nombre])
        Producto.objects.filter(pk=producto.pk).update(texto_busqueda=normalizar(texto))


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0003_marcas_asus_vsg"),
    ]

    operations = [
        migrations.AddField(
            model_name="producto",
            name="precio_oferta",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Opcional. Debe ser menor que el precio normal.",
                max_digits=8,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(
                        decimal.Decimal("0.10"),
                        message="El precio debe ser de al menos S/ 0.10.",
                    )
                ],
                verbose_name="precio de oferta (S/)",
            ),
        ),
        migrations.AddField(
            model_name="producto",
            name="oferta_hasta",
            field=models.DateField(
                blank=True,
                help_text="Opcional. Ese día es el último de la oferta; vacío = hasta que la quites.",
                null=True,
                verbose_name="oferta válida hasta",
            ),
        ),
        migrations.AddField(
            model_name="producto",
            name="destacado",
            field=models.BooleanField(
                default=False,
                help_text="Aparece en la sección de destacados de la página de inicio. Máximo 3 por tienda.",
                verbose_name="destacado en el inicio",
            ),
        ),
        migrations.AddField(
            model_name="producto",
            name="texto_busqueda",
            field=models.TextField(blank=True, editable=False, verbose_name="texto de búsqueda"),
        ),
        migrations.CreateModel(
            name="FotoProducto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "imagen",
                    models.ImageField(
                        upload_to="productos/fotos/",
                        validators=[
                            django.core.validators.FileExtensionValidator(
                                allowed_extensions=["jpg", "jpeg", "png", "webp"]
                            ),
                            catalogo.models.validar_tamano_imagen,
                        ],
                        verbose_name="imagen",
                    ),
                ),
                ("orden", models.PositiveSmallIntegerField(default=0, verbose_name="orden")),
                (
                    "producto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fotos",
                        to="catalogo.producto",
                        verbose_name="producto",
                    ),
                ),
            ],
            options={
                "verbose_name": "foto del producto",
                "verbose_name_plural": "fotos del producto",
                "ordering": ["orden", "id"],
            },
        ),
        migrations.RunPython(llenar_texto_busqueda, migrations.RunPython.noop),
    ]
