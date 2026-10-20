"""
Dónde se guarda cada imagen subida: una carpeta por tienda.

    media/tiendas/3-tecno-quillabamba/
        logo/logo.webp
        productos/laptop-asus-tuf-a15.webp
        productos/fotos/laptop-asus-tuf-a15-foto-1.webp

- La carpeta lleva el NÚMERO de la tienda delante del nombre: los nombres pueden
  cambiar o parecerse, el número no.
- Cada archivo se llama como el producto, así se sabe qué es sin abrirlo.
- Si ya existe un archivo con ese nombre, Django le agrega unas letras al final.
- Si una tienda o un producto cambia de nombre, sus imágenes se quedan donde
  estaban; para reordenarlas: python manage.py ordenar_imagenes

Este archivo no importa modelos, para que tiendas y catálogo puedan usarlo.
"""

import os

from django.utils.text import slugify


def _extension(nombre_archivo):
    return os.path.splitext(nombre_archivo)[1].lower() or ".webp"


def _corto(texto, por_defecto, largo):
    return slugify(texto or "")[:largo].strip("-") or por_defecto


def carpeta_tienda(tienda):
    numero = tienda.pk if tienda.pk else "nueva"
    return f"tiendas/{numero}-{_corto(tienda.nombre, 'tienda', 40)}"


def ruta_logo_tienda(tienda, nombre_archivo):
    return f"{carpeta_tienda(tienda)}/logo/logo{_extension(nombre_archivo)}"


def ruta_imagen_producto(producto, nombre_archivo):
    return (
        f"{carpeta_tienda(producto.tienda)}/productos/"
        f"{_corto(producto.nombre, 'producto', 60)}{_extension(nombre_archivo)}"
    )


def ruta_foto_producto(foto, nombre_archivo):
    producto = foto.producto
    return (
        f"{carpeta_tienda(producto.tienda)}/productos/fotos/"
        f"{_corto(producto.nombre, 'producto', 60)}-foto-{foto.orden or 1}{_extension(nombre_archivo)}"
    )
