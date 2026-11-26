"""
Nov 2026:
- 16 íconos nuevos para las categorías (de 22 a 38).
- Color de la etiqueta de cada marca, que ahora elige el administrador. Las marcas que ya tenían
  un color en marca.css lo conservan; las demás quedan en azul marino (#0B1B3A).
"""

import django.core.validators
from django.db import migrations, models
from django.utils.text import slugify

COLORES_ANTERIORES = {
    "samsung": "#1428A0",
    "lenovo": "#C8102E", "nintendo": "#C8102E", "canon": "#C8102E", "hyperx": "#C8102E", "redragon": "#C8102E",
    "kingston": "#141414", "sony": "#141414", "corsair": "#141414", "amazfit": "#141414", "logitech": "#141414",
    "amd": "#141414",
    "asus": "#5B34C9",
    "apple": "#5F6B7A",
    "epson": "#1A56C4",
    "xiaomi": "#B8470B", "jbl": "#B8470B",
    "lg": "#A50034",
    "hp": "#0063A6",
    "motorola": "#1E3A8A",
    "infinix": "#2E7D32", "acer": "#2E7D32",
    "tp-link": "#0B6E7E", "ezviz": "#0B6E7E", "hisense": "#0B6E7E",
    "soundcore-anker": "#1D4ED8",
}


def pasar_colores(apps, schema_editor):
    Marca = apps.get_model("catalogo", "Marca")
    for marca in Marca.objects.all():
        color = COLORES_ANTERIORES.get(slugify(marca.nombre))
        if color:
            Marca.objects.filter(pk=marca.pk).update(color=color)


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0012_producto_republicado_el"),
    ]

    operations = [
        migrations.AlterField(
            model_name="categoria",
            name="icono",
            field=models.CharField(
                choices=[
                    ("phone", "Celular"),
                    ("laptop", "Laptop"),
                    ("pc-display", "Computadora de escritorio"),
                    ("tablet", "Tablet"),
                    ("pen", "Lápiz digital"),
                    ("display", "Monitor"),
                    ("tv", "Televisor"),
                    ("projector", "Proyector"),
                    ("headphones", "Audífonos"),
                    ("earbuds", "Audífonos inalámbricos"),
                    ("speaker", "Parlante"),
                    ("soundwave", "Bocina inteligente"),
                    ("mic", "Micrófono"),
                    ("keyboard", "Teclado y accesorios"),
                    ("mouse", "Mouse"),
                    ("webcam", "Cámara web"),
                    ("printer", "Impresora"),
                    ("cpu", "Componentes / repuestos"),
                    ("motherboard", "Placa madre"),
                    ("gpu-card", "Tarjeta de video"),
                    ("memory", "Memoria RAM"),
                    ("fan", "Refrigeración"),
                    ("usb-drive", "Almacenamiento"),
                    ("device-ssd", "Disco SSD"),
                    ("camera-video", "Cámara de seguridad"),
                    ("camera", "Cámara de fotos"),
                    ("smartwatch", "Smartwatch"),
                    ("controller", "Videojuegos"),
                    ("router", "Redes / router"),
                    ("sim", "Chip / SIM"),
                    ("house-gear", "Casa inteligente"),
                    ("lightbulb", "Iluminación"),
                    ("battery-charging", "Energía / UPS"),
                    ("battery-full", "Power bank"),
                    ("plug", "Cables y cargadores"),
                    ("disc", "Software y licencias"),
                    ("tools", "Servicio técnico"),
                    ("grid", "Otros"),
                ],
                default="grid",
                help_text="Se ve junto al nombre en «Todas las categorías».",
                max_length=30,
                verbose_name="ícono",
            ),
        ),
        migrations.AddField(
            model_name="marca",
            name="color",
            field=models.CharField(
                default="#0B1B3A",
                help_text="Fondo de la etiqueta con el nombre de la marca en las tarjetas de producto.",
                max_length=7,
                validators=[
                    django.core.validators.RegexValidator(
                        "^#[0-9A-Fa-f]{6}$", "Escribe el color como #RRGGBB (por ejemplo #1428A0)."
                    )
                ],
                verbose_name="color de la etiqueta",
            ),
        ),
        migrations.RunPython(pasar_colores, migrations.RunPython.noop),
    ]
