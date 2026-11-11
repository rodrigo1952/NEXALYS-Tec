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


# --- Miniaturas -------------------------------------------------------------------------------
# Las tarjetas del catálogo no necesitan la foto de 1200 px: usan una copia chica que pesa mucho menos.
# Se crean la primera vez que una página las pide (y con: python manage.py crear_miniaturas) y se
# guardan en media/miniaturas/<tipo>/... Al borrar la foto original, se borran también (almacenamiento.py).
CARPETA_MINIATURAS = "miniaturas"
MINIATURAS = {
    "tarjeta": (600, "WEBP"),    # tarjetas del catálogo, inicio, favoritos y la tienda
    "icono": (160, "WEBP"),      # miniaturas pequeñas (tabla de Mis productos, galería del detalle)
    "compartir": (600, "JPEG"),  # foto de la vista previa al compartir el enlace (WhatsApp, Facebook)
}


def ruta_miniatura(nombre, tipo):
    """productos/tienda/laptop.webp → miniaturas/tarjeta/productos/tienda/laptop.webp"""
    lado, formato = MINIATURAS[tipo]
    extension = ".jpg" if formato == "JPEG" else ".webp"
    return f"{CARPETA_MINIATURAS}/{tipo}/{os.path.splitext(nombre)[0]}{extension}"


def _guardar_miniatura(origen, destino, tipo):
    lado, formato = MINIATURAS[tipo]
    with Image.open(origen) as original:
        imagen = ImageOps.exif_transpose(original)
        if formato == "JPEG":
            # JPEG no tiene transparencia: los logos transparentes van sobre fondo blanco.
            imagen = imagen.convert("RGBA")
            fondo = Image.new("RGB", imagen.size, "white")
            fondo.paste(imagen, mask=imagen.split()[3])
            imagen = fondo
        elif imagen.mode not in ("RGB", "RGBA"):
            imagen = imagen.convert("RGBA" if imagen.mode in ("LA", "P") else "RGB")
        imagen.thumbnail((lado, lado))
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        temporal = f"{destino}.{os.getpid()}.tmp"
        imagen.save(temporal, format=formato, quality=80 if formato == "JPEG" else CALIDAD_WEBP)
    os.replace(temporal, destino)  # aparece completa de una vez, aunque dos visitas la pidan juntas


def url_miniatura(campo, tipo="tarjeta"):
    """
    Dirección de la miniatura de una imagen (la crea si falta o si la original es más nueva).
    Si algo falla, devuelve la imagen original: la página nunca se queda sin foto.
    """
    if not campo:
        return ""
    almacenamiento = campo.storage
    ruta = ruta_miniatura(campo.name, tipo)
    try:
        origen, destino = almacenamiento.path(campo.name), almacenamiento.path(ruta)
        if not os.path.exists(destino) or os.path.getmtime(destino) < os.path.getmtime(origen):
            _guardar_miniatura(origen, destino, tipo)
        return almacenamiento.url(ruta)
    except Exception:  # p. ej. la original no existe o el almacenamiento no es una carpeta
        return campo.url
