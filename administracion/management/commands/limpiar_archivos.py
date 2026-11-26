"""
Busca archivos sueltos en media/: fotos, logos y miniaturas que ya no usa ningún producto
ni ninguna tienda (por ejemplo, de algo que se borró antes de nov 2026 o a mano en la carpeta).

Uso:
    python manage.py limpiar_archivos            → solo muestra qué borraría (no toca nada)
    python manage.py limpiar_archivos --borrar   → los borra y quita las carpetas que quedan vacías

Solo revisa media/tiendas/ y media/miniaturas/<tipo>/tiendas/. Desde nov 2026, al eliminar un
producto o una tienda sus archivos se borran solos (catalogo/models.py y tiendas/baja.py); este
comando es para ordenar lo que haya quedado de antes, por ejemplo en el servidor al publicar.
"""

import os

from django.conf import settings
from django.core.management.base import BaseCommand

from catalogo.imagenes import CARPETA_MINIATURAS, MINIATURAS, ruta_miniatura
from catalogo.models import FotoProducto, Producto
from catalogo.reubicar import borrar_carpetas_vacias
from tiendas.models import Tienda


def zonas():
    """Carpetas (relativas a media/) donde viven las imágenes de las tiendas."""
    return ["tiendas"] + [f"{CARPETA_MINIATURAS}/{tipo}/tiendas" for tipo in MINIATURAS]


def archivos_en_uso():
    """Las imágenes que usa algún producto o tienda, y las miniaturas que les corresponden."""
    nombres = set()
    for modelo, campo in ((Producto, "imagen"), (FotoProducto, "imagen"), (Tienda, "logo")):
        nombres.update(nombre for nombre in modelo.objects.values_list(campo, flat=True) if nombre)
    miniaturas = {ruta_miniatura(nombre, tipo) for nombre in nombres for tipo in MINIATURAS}
    return {ruta.replace("\\", "/") for ruta in nombres | miniaturas}


def archivos_sueltos():
    """[(ruta relativa a media/, bytes)] de los archivos que nadie usa."""
    en_uso = archivos_en_uso()
    sueltos = []
    for zona in zonas():
        base = os.path.join(settings.MEDIA_ROOT, zona)
        for carpeta, _subcarpetas, archivos in os.walk(base):
            for archivo in archivos:
                ruta = os.path.join(carpeta, archivo)
                relativa = os.path.relpath(ruta, settings.MEDIA_ROOT).replace(os.sep, "/")
                if relativa not in en_uso:
                    sueltos.append((relativa, os.path.getsize(ruta)))
    return sorted(sueltos)


def carpetas_de_tiendas():
    """Las carpetas de cada tienda dentro de cada zona (tiendas/3-selva-byte, miniaturas/tarjeta/tiendas/3-…)."""
    for zona in zonas():
        base = os.path.join(settings.MEDIA_ROOT, zona)
        if os.path.isdir(base):
            for nombre in sorted(os.listdir(base)):
                if os.path.isdir(os.path.join(base, nombre)):
                    yield f"{zona}/{nombre}"


def _tamano(bytes_):
    return f"{bytes_ / 1024 / 1024:.2f} MB" if bytes_ >= 1024 * 1024 else f"{bytes_ / 1024:.0f} KB"


class Command(BaseCommand):
    help = "Muestra (o borra con --borrar) las imágenes de media/ que ya no usa ningún producto ni tienda."

    def add_arguments(self, parser):
        parser.add_argument("--borrar", action="store_true", help="Borra los archivos sueltos y las carpetas vacías.")

    def handle(self, *args, **opciones):
        sueltos = archivos_sueltos()
        total = sum(tamano for _ruta, tamano in sueltos)
        for ruta, tamano in sueltos:
            self.stdout.write(f"  {ruta}  ({_tamano(tamano)})")

        if not opciones["borrar"]:
            if sueltos:
                self.stdout.write(self.style.WARNING(
                    f"Archivos sueltos: {len(sueltos)} ({_tamano(total)}). No se borró nada: "
                    "para borrarlos, usa  python manage.py limpiar_archivos --borrar"
                ))
            else:
                self.stdout.write(self.style.SUCCESS("No hay archivos sueltos. Todo en orden."))
            return

        for ruta, _tamano_archivo in sueltos:
            try:
                os.remove(os.path.join(settings.MEDIA_ROOT, ruta))
            except OSError:
                pass
        for carpeta in carpetas_de_tiendas():
            borrar_carpetas_vacias(carpeta)
        self.stdout.write(self.style.SUCCESS(
            f"Se borraron {len(sueltos)} archivo(s) suelto(s) ({_tamano(total)}) y las carpetas que quedaron vacías."
        ))
