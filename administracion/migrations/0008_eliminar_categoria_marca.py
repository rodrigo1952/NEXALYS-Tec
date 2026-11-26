"""
Nov 2026: el historial también anota cuando el administrador elimina una categoría o una marca
(y a dónde pasaron sus productos).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("administracion", "0007_visitaqr"),
    ]

    operations = [
        migrations.AlterField(
            model_name="accionadmin",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("suspender_tienda", "Suspendió una tienda"),
                    ("reactivar_tienda", "Reactivó una tienda"),
                    ("desactivar_cuenta", "Desactivó una cuenta"),
                    ("reactivar_cuenta", "Reactivó una cuenta"),
                    ("eliminar_cuenta", "Eliminó una cuenta"),
                    ("ocultar_producto", "Ocultó un producto"),
                    ("mostrar_producto", "Volvió a mostrar un producto"),
                    ("eliminacion_auto", "Eliminación automática (90 días suspendida)"),
                    ("restablecer_clave", "Restableció una contraseña"),
                    ("responder_derecho", "Respondió una solicitud de datos personales"),
                    ("responder_reclamo", "Respondió una hoja del Libro de Reclamaciones"),
                    ("eliminar_categoria", "Eliminó una categoría"),
                    ("eliminar_marca", "Eliminó una marca"),
                ],
                max_length=20,
                verbose_name="acción",
            ),
        ),
    ]
