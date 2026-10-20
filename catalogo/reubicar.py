"""
Mueve imágenes a la ruta que les corresponde según el nombre ACTUAL de la tienda y del producto.

Se usa en dos momentos:
  - Automáticamente, cuando una tienda o un producto cambia de nombre (Opción A):
    Producto.save() y Tienda.save() llaman a reubicar_producto / reubicar_tienda
    DESPUÉS de que los datos se guardaron con éxito (transaction.on_commit).
  - A mano, con: python manage.py ordenar_imagenes

Seguridad: cada imagen primero se copia a la ruta nueva, luego se actualiza la base de
datos y recién al final se borra la copia vieja. Si algo falla, la imagen se queda
donde estaba y la página sigue mostrándola: nunca se pierde una imagen.
"""

import logging
import os
from types import SimpleNamespace

from django.conf import settings
from django.core.files import File

from .archivos import carpeta_tienda, ruta_foto_producto, ruta_imagen_producto, ruta_logo_tienda

registro = logging.getLogger(__name__)

MOVIDA, ORDENADA, FALTA, ERROR = "movida", "ordenada", "falta", "error"


def ya_esta_ordenada(actual, deseada):
    """Misma carpeta y el nombre empieza igual (Django puede haber agregado letras al final)."""
    raiz_deseada = os.path.splitext(os.path.basename(deseada))[0]
    return (
        os.path.dirname(actual) == os.path.dirname(deseada)
        and os.path.basename(actual).startswith(raiz_deseada)
    )


def mover_archivo(objeto, campo, calcular_ruta, simular=False):
    """Mueve la imagen de objeto.<campo> a su ruta correcta. Devuelve MOVIDA, ORDENADA o FALTA."""
    archivo = getattr(objeto, campo)
    actual = archivo.name
    if not actual:
        return ORDENADA
    deseada = calcular_ruta(objeto, os.path.basename(actual))
    if ya_esta_ordenada(actual, deseada):
        return ORDENADA
    almacenamiento = archivo.storage
    if not almacenamiento.exists(actual):
        return FALTA
    if simular:
        return MOVIDA
    with almacenamiento.open(actual, "rb") as contenido:
        nueva = almacenamiento.save(deseada, File(contenido))
    try:
        # update() en lugar de save(): no se vuelve a optimizar ni se dispara otra reubicación.
        type(objeto).objects.filter(pk=objeto.pk).update(**{campo: nueva})
    except Exception:
        almacenamiento.delete(nueva)  # si falla la base de datos, todo queda como estaba
        raise
    almacenamiento.delete(actual)
    archivo.name = nueva
    return MOVIDA


def mover_sin_romper(objeto, campo, calcular_ruta):
    """Igual que mover_archivo, pero un error no interrumpe la página: se anota y se sigue."""
    try:
        return mover_archivo(objeto, campo, calcular_ruta)
    except Exception:
        registro.exception("No se pudo mover la imagen %s de %r", getattr(objeto, campo).name, objeto)
        return ERROR


def _reubicar_imagenes_de(producto):
    mover_sin_romper(producto, "imagen", ruta_imagen_producto)
    for foto in producto.fotos.all():
        foto.producto = producto  # evita volver a consultar la tienda por cada foto
        mover_sin_romper(foto, "imagen", ruta_foto_producto)


def reubicar_producto(producto_id):
    """El producto cambió de nombre: su imagen y sus fotos toman el nombre nuevo."""
    from .models import Producto

    producto = Producto.objects.select_related("tienda").filter(pk=producto_id).first()
    if producto is not None:
        _reubicar_imagenes_de(producto)


def reubicar_tienda(tienda_id, nombre_anterior):
    """La tienda cambió de nombre: su logo y todas las imágenes de sus productos van a la carpeta nueva."""
    from tiendas.models import Tienda

    tienda = Tienda.objects.filter(pk=tienda_id).first()
    if tienda is None:
        return
    mover_sin_romper(tienda, "logo", ruta_logo_tienda)
    for producto in tienda.productos.prefetch_related("fotos"):
        producto.tienda = tienda
        _reubicar_imagenes_de(producto)
    borrar_carpetas_vacias(carpeta_tienda(SimpleNamespace(pk=tienda_id, nombre=nombre_anterior)))


def borrar_carpetas_vacias(relativa):
    """Borra las carpetas vacías dentro de media/<relativa> (y esa misma si queda vacía)."""
    raiz = os.path.join(settings.MEDIA_ROOT, relativa)
    if not os.path.isdir(raiz):
        return
    for carpeta, _subcarpetas, _archivos in os.walk(raiz, topdown=False):
        try:
            if not os.listdir(carpeta):
                os.rmdir(carpeta)
        except OSError:
            pass
