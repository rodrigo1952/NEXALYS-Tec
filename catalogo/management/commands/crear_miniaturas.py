"""
Crea de una vez las miniaturas de todas las fotos de productos y logos de tiendas.

Uso:  python manage.py crear_miniaturas
No es obligatorio (las páginas las crean solas la primera vez), pero conviene correrlo después de
publicar o de cargar muchas fotos, para que la primera visita no espere.
"""

from django.core.management.base import BaseCommand

from catalogo.imagenes import url_miniatura
from catalogo.models import FotoProducto, Producto
from tiendas.models import Tienda


class Command(BaseCommand):
    help = "Crea las miniaturas de todas las fotos de productos y logos (las que ya existen no se repiten)."

    def handle(self, *args, **opciones):
        total = 0
        for producto in Producto.objects.exclude(imagen=""):
            for tipo in ("tarjeta", "icono", "compartir"):
                url_miniatura(producto.imagen, tipo)
            total += 1
        for foto in FotoProducto.objects.exclude(imagen=""):
            url_miniatura(foto.imagen, "icono")
            total += 1
        for tienda in Tienda.objects.exclude(logo=""):
            url_miniatura(tienda.logo, "compartir")
            total += 1
        self.stdout.write(self.style.SUCCESS(f"Listo: {total} imágenes revisadas."))
