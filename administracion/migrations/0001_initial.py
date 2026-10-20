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
            name="AccionAdmin",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="fecha")),
                ("admin_nombre", models.CharField(max_length=150, verbose_name="administrador (nombre)")),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("suspender_tienda", "Suspendió una tienda"),
                            ("reactivar_tienda", "Reactivó una tienda"),
                            ("desactivar_cuenta", "Desactivó una cuenta"),
                            ("reactivar_cuenta", "Reactivó una cuenta"),
                            ("eliminar_cuenta", "Eliminó una cuenta"),
                            ("ocultar_producto", "Ocultó un producto"),
                            ("mostrar_producto", "Volvió a mostrar un producto"),
                        ],
                        max_length=20,
                        verbose_name="acción",
                    ),
                ),
                ("objetivo", models.CharField(max_length=250, verbose_name="sobre")),
                ("motivo", models.TextField(blank=True, verbose_name="motivo")),
                (
                    "admin",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="acciones_realizadas",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="administrador",
                    ),
                ),
                (
                    "usuario_afectado",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="acciones_recibidas",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="cuenta afectada",
                    ),
                ),
            ],
            options={
                "verbose_name": "acción del administrador",
                "verbose_name_plural": "historial del administrador",
                "ordering": ["-fecha", "-id"],
            },
        ),
    ]
