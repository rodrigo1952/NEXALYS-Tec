"""
Optimización de imágenes subidas (productos, fotos extra y logos de tiendas).

Antes de guardar, cada imagen nueva:
  1. Se gira según la orientación de la cámara (fotos de celular que salían de costado).
  2. Se reduce para que su lado mayor no pase de un límite (solo reduce, nunca agranda).
  3. Se guarda en formato WEBP, que pesa mucho menos que JPG o PNG con la misma calidad.
Una foto de celular de 4 MB suele quedar en menos de 200 KB, y la página carga más rápido.
"""

import io
import os

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

LADO_MAXIMO_PRODUCTO = 1200
LADO_MAXIMO_LOGO = 400
CALIDAD_WEBP = 82


def optimizar_imagen(archivo, lado_maximo, calidad=CALIDAD_WEBP):
    """Devuelve un ContentFile .webp con la imagen girada, reducida y comprimida."""
    archivo.seek(0)
    with Image.open(archivo) as original:
        imagen = ImageOps.exif_transpose(original)
        if imagen.mode in ("RGBA", "LA", "P"):
            imagen = imagen.convert("RGBA")  # conserva la transparencia (logos)
        else:
            imagen = imagen.convert("RGB")
        imagen.thumbnail((lado_maximo, lado_maximo))
        salida = io.BytesIO()
        imagen.save(salida, format="WEBP", quality=calidad)
    nombre = os.path.splitext(os.path.basename(archivo.name))[0] + ".webp"
    return ContentFile(salida.getvalue(), name=nombre)


def optimizar_campo(campo, lado_maximo):
    """
    Si el campo tiene una imagen recién subida (aún no guardada), la reemplaza
    por su versión optimizada. Las imágenes que ya estaban guardadas no se tocan.
    """
    if not campo or getattr(campo, "_committed", True):
        return
    try:
        optimizada = optimizar_imagen(campo.file, lado_maximo)
    except Exception:  # si Pillow no puede procesarla, se guarda la original
        return
    campo.save(optimizada.name, optimizada, save=False)
