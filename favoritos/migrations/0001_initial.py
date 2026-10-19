import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("catalogo", "0003_marcas_asus_vsg"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Favorito",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("precio_guardado", models.DecimalField(decimal_places=2, max_digits=8, verbose_name="precio al guardarlo")),
                ("precio_visto", models.DecimalField(decimal_places=2, max_digits=8, verbose_name="precio en la última revisión")),
                ("agotado_visto", models.BooleanField(default=False, verbose_name="agotado en la última revisión")),
                ("creado", models.DateTimeField(auto_now_add=True, verbose_name="guardado el")),
                (
                    "producto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="favoritos",
                        to="catalogo.producto",
                        verbose_name="producto",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="favoritos",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="cliente",
                    ),
                ),
            ],
            options={
                "verbose_name": "favorito",
                "verbose_name_plural": "favoritos",
                "ordering": ["-creado"],
                "constraints": [
                    models.UniqueConstraint(fields=("usuario", "producto"), name="favorito_unico_por_usuario"),
                ],
            },
        ),
    ]
