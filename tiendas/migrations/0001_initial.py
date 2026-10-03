import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Tienda",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=100, unique=True, verbose_name="nombre de la tienda")),
                ("direccion", models.CharField(max_length=200, verbose_name="dirección")),
                (
                    "whatsapp",
                    models.CharField(
                        help_text="9 dígitos, sin +51 ni espacios. Ejemplo: 987654321",
                        max_length=9,
                        unique=True,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Ingresa un número de celular peruano de 9 dígitos que empiece con 9.",
                                regex="^9\\d{8}$",
                            )
                        ],
                        verbose_name="WhatsApp",
                    ),
                ),
                ("descripcion", models.TextField(blank=True, verbose_name="descripción")),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("pendiente", "Pendiente de verificación"),
                            ("activa", "Activa"),
                            ("suspendida", "Suspendida"),
                        ],
                        default="pendiente",
                        max_length=12,
                        verbose_name="estado",
                    ),
                ),
                ("verificada_en", models.DateTimeField(blank=True, null=True, verbose_name="correo verificado el")),
                ("creada_en", models.DateTimeField(auto_now_add=True, verbose_name="registrada el")),
                (
                    "usuario",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tienda",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="usuario",
                    ),
                ),
            ],
            options={
                "verbose_name": "tienda",
                "verbose_name_plural": "tiendas",
                "ordering": ["nombre"],
            },
        ),
    ]
