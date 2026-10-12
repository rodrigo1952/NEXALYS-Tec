import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("catalogo", "0003_marcas_asus_vsg"),
        ("tiendas", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Pedido",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cliente_nombre", models.CharField(max_length=100, verbose_name="nombre del cliente")),
                (
                    "cliente_telefono",
                    models.CharField(
                        help_text="9 dígitos. Ejemplo: 987654321",
                        max_length=9,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="Ingresa un número de celular peruano de 9 dígitos que empiece con 9.",
                                regex="^9\\d{8}$",
                            )
                        ],
                        verbose_name="celular del cliente",
                    ),
                ),
                (
                    "cantidad",
                    models.PositiveIntegerField(
                        validators=[django.core.validators.MinValueValidator(1, message="La cantidad mínima es 1.")],
                        verbose_name="cantidad",
                    ),
                ),
                ("precio_unitario", models.DecimalField(decimal_places=2, max_digits=8, verbose_name="precio unitario (S/)")),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("pendiente", "Pendiente"),
                            ("confirmado", "Confirmado"),
                            ("entregado", "Entregado"),
                            ("cancelado", "Cancelado"),
                        ],
                        default="pendiente",
                        max_length=12,
                        verbose_name="estado",
                    ),
                ),
                ("observacion", models.TextField(blank=True, verbose_name="observación")),
                ("creado", models.DateTimeField(auto_now_add=True, verbose_name="registrado")),
                ("actualizado", models.DateTimeField(auto_now=True, verbose_name="actualizado")),
                (
                    "producto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="pedidos",
                        to="catalogo.producto",
                        verbose_name="producto",
                    ),
                ),
                (
                    "tienda",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pedidos",
                        to="tiendas.tienda",
                        verbose_name="tienda",
                    ),
                ),
            ],
            options={
                "verbose_name": "pedido",
                "verbose_name_plural": "pedidos",
                "ordering": ["-creado"],
            },
        ),
    ]
