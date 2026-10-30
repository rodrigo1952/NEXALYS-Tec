"""
Ícono de cada categoría (lo elige el administrador). Las categorías que ya existen
reciben el ícono que les corresponde por su nombre.
"""

from django.db import migrations, models

ICONOS_INICIALES = {
    "accesorios": "keyboard",
    "audio": "headphones",
    "celulares": "phone",
    "computadoras de escritorio": "pc-display",
    "impresoras y suministros": "printer",
    "laptops": "laptop",
    "otros": "grid",
    "pantallas": "display",
    "repuestos": "cpu",
    "seguridad y videovigilancia": "camera-video",
    "tablets": "tablet",
}


def poner_iconos(apps, schema_editor):
    Categoria = apps.get_model("catalogo", "Categoria")
    for categoria in Categoria.objects.all():
        icono = ICONOS_INICIALES.get(categoria.nombre.lower())
        if icono:
            Categoria.objects.filter(pk=categoria.pk).update(icono=icono)


class Migration(migrations.Migration):
    dependencies = [("catalogo", "0009_categorias_y_marcas_nuevas")]

    operations = [
        migrations.AddField(
            model_name="categoria",
            name="icono",
            field=models.CharField(
                choices=[
                    ("phone", "Celular"), ("laptop", "Laptop"), ("pc-display", "Computadora de escritorio"),
                    ("tablet", "Tablet"), ("display", "Monitor"), ("tv", "Televisor"), ("headphones", "Audífonos"),
                    ("speaker", "Parlante"), ("keyboard", "Teclado y accesorios"), ("mouse", "Mouse"),
                    ("printer", "Impresora"), ("cpu", "Componentes / repuestos"), ("usb-drive", "Almacenamiento"),
                    ("camera-video", "Cámara de seguridad"), ("camera", "Cámara de fotos"),
                    ("smartwatch", "Smartwatch"), ("controller", "Videojuegos"), ("router", "Redes / router"),
                    ("battery-charging", "Energía / UPS"), ("plug", "Cables y cargadores"),
                    ("tools", "Servicio técnico"), ("grid", "Otros"),
                ],
                default="grid",
                help_text="Se ve junto al nombre en «Todas las categorías».",
                max_length=30,
                verbose_name="ícono",
            ),
        ),
        migrations.RunPython(poner_iconos, migrations.RunPython.noop),
    ]
