"""
Fecha de suspensión: una tienda suspendida que no se reactiva en 90 días se elimina sola.
Las tiendas que ya estaban suspendidas empiezan a contar desde hoy.
"""

from django.db import migrations, models
from django.utils import timezone


def iniciar_cuenta_regresiva(apps, schema_editor):
    Tienda = apps.get_model("tiendas", "Tienda")
    Tienda.objects.filter(estado="suspendida", suspendida_en__isnull=True).update(suspendida_en=timezone.now())


class Migration(migrations.Migration):

    dependencies = [
        ("tiendas", "0005_logo_por_tienda"),
    ]

    operations = [
        migrations.AddField(
            model_name="tienda",
            name="suspendida_en",
            field=models.DateTimeField(blank=True, null=True, verbose_name="suspendida el"),
        ),
        migrations.RunPython(iniciar_cuenta_regresiva, migrations.RunPython.noop),
    ]
