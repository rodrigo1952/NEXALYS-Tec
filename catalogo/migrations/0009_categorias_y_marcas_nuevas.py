"""
Agrega las categorías y marcas que el equipo eligió de la lista de investigación
(tiendas grandes de tecnología del Perú, octubre 2026). Si alguna ya existe, no se duplica.
"""

from django.db import migrations

CATEGORIAS = [
    "Computadoras de escritorio",
    "Impresoras y suministros",
    "Otros",
    "Repuestos",
    "Seguridad y videovigilancia",
    "Tablets",
]

MARCAS = [
    "ADATA", "Amazfit", "Amazon", "AMD", "AOC", "APC", "ASRock", "Baseus", "Bose", "Brother",
    "Canon", "Cooler Master", "Corsair", "Crucial", "Dahua", "Dell", "DJI", "Epson", "Ezviz", "Forza",
    "Gigabyte", "GoPro", "Halion", "Havit", "Hikvision", "Hisense", "Honor", "Huawei", "HyperX", "Infinix",
    "Intel", "Kingston", "LG", "Mercusys", "Micronics", "Microsoft", "Motorola", "MSI", "Nintendo", "OPPO",
    "Philips", "Razer", "realme", "Redragon", "SanDisk", "Seagate", "Sony", "Soundcore (Anker)", "TCL", "Tecno",
    "Tenda", "Teros", "TP-Link", "Trust", "vivo", "Western Digital", "ZTE",
]


def _crear(modelo, nombres):
    for nombre in nombres:
        # Sin importar mayúsculas: si ya existe "lg" no se crea "LG".
        if not modelo.objects.filter(nombre__iexact=nombre).exists():
            modelo.objects.create(nombre=nombre)


def agregar(apps, schema_editor):
    _crear(apps.get_model("catalogo", "Categoria"), CATEGORIAS)
    _crear(apps.get_model("catalogo", "Marca"), MARCAS)


def quitar(apps, schema_editor):
    # Al revertir solo se borran las que ningún producto usa.
    apps.get_model("catalogo", "Categoria").objects.filter(nombre__in=CATEGORIAS, productos__isnull=True).delete()
    apps.get_model("catalogo", "Marca").objects.filter(nombre__in=MARCAS, productos__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0008_imagenes_por_tienda"),
    ]

    operations = [
        migrations.RunPython(agregar, quitar),
    ]
