import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

import catalogo.models


class Migration(migrations.Migration):

    dependencies = [
        ("tiendas", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="tienda",
            name="logo",
            field=models.ImageField(
                blank=True,
                help_text="Opcional. JPG, PNG o WEBP de máximo 2 MB. Se recomienda una imagen cuadrada.",
                upload_to="tiendas/logos/",
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=["jpg", "jpeg", "png", "webp"]
                    ),
                    catalogo.models.validar_tamano_imagen,
                ],
                verbose_name="logo",
            ),
        ),
        migrations.CreateModel(
            name="HorarioDia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "dia",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "Lunes"),
                            (1, "Martes"),
                            (2, "Miércoles"),
                            (3, "Jueves"),
                            (4, "Viernes"),
                            (5, "Sábado"),
                            (6, "Domingo"),
                        ],
                        verbose_name="día",
                    ),
                ),
                ("abre", models.TimeField(blank=True, null=True, verbose_name="abre")),
                ("cierra", models.TimeField(blank=True, null=True, verbose_name="cierra")),
                (
                    "tienda",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="horarios",
                        to="tiendas.tienda",
                        verbose_name="tienda",
                    ),
                ),
            ],
            options={
                "verbose_name": "horario",
                "verbose_name_plural": "horarios",
                "ordering": ["dia"],
                "constraints": [
                    models.UniqueConstraint(fields=("tienda", "dia"), name="horario_unico_por_dia"),
                ],
            },
        ),
    ]
