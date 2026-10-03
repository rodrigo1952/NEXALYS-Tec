"""Carga las categorías y marcas iniciales del catálogo (el administrador puede agregar más)."""

from django.db import migrations

CATEGORIAS = ["Accesorios", "Audio", "Celulares", "Laptops"]
MARCAS = ["Apple", "HP", "JBL", "Lenovo", "Logitech", "Samsung", "Xiaomi", "Otra"]


def cargar(apps, schema_editor):
    Categoria = apps.get_model("catalogo", "Categoria")
    Marca = apps.get_model("catalogo", "Marca")
    for nombre in CATEGORIAS:
        Categoria.objects.get_or_create(nombre=nombre)
    for nombre in MARCAS:
        Marca.objects.get_or_create(nombre=nombre)


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
