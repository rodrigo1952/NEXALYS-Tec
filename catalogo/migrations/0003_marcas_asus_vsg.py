"""Agrega las marcas Asus y VSG al catálogo."""

from django.db import migrations

MARCAS = ["Asus", "VSG"]


def agregar(apps, schema_editor):
    Marca = apps.get_model("catalogo", "Marca")
    for nombre in MARCAS:
        Marca.objects.get_or_create(nombre=nombre)


def quitar(apps, schema_editor):
    Marca = apps.get_model("catalogo", "Marca")
    Marca.objects.filter(nombre__in=MARCAS, productos__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0002_datos_iniciales"),
    ]

    operations = [
        migrations.RunPython(agregar, quitar),
    ]