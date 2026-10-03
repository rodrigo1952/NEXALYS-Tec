"""El rol 'Vendedor' pasa a llamarse 'Tienda', como en la ficha de casos de uso."""

from django.db import migrations


def renombrar(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    if Group.objects.filter(name="Tienda").exists():
        Group.objects.filter(name="Vendedor").delete()
    else:
        Group.objects.filter(name="Vendedor").update(name="Tienda")
    Group.objects.get_or_create(name="Tienda")


def revertir(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Tienda").update(name="Vendedor")


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0001_crear_roles"),
    ]

    operations = [
        migrations.RunPython(renombrar, revertir),
    ]
