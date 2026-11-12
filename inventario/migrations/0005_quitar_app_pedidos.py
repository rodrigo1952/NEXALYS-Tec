"""
Se quitó la app «pedidos» (estaba vacía desde la Etapa 5: sus pedidos ya son ventas).
Se borran los restos que dejó en la base de datos: su tipo de contenido (y sus permisos)
y el registro de sus migraciones. Si no hay restos, no hace nada.
"""

from django.db import migrations
from django.db.migrations.recorder import MigrationRecorder


def limpiar(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.using(schema_editor.connection.alias).filter(app_label="pedidos").delete()
    MigrationRecorder(schema_editor.connection).migration_qs.filter(app="pedidos").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0004_convertir_pedidos"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(limpiar, migrations.RunPython.noop),
    ]
