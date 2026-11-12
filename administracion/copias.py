"""
Copias de seguridad: la base de datos y las fotos en un solo archivo .zip.

  - Se crean cada día con:  python manage.py copia_seguridad   (tarea programada en el hosting)
    y cuando el administrador presiona «Crear copia ahora» en la consola (Control → Copias).
  - Se guardan en la carpeta copias/ (junto a manage.py; no va a GitHub) y se borran solas
    las de más de DIAS_GUARDADAS días (siempre queda al menos la más reciente).
  - Desde la consola se descargan para guardar una en tu PC, por si el servidor se pierde.
  - Para volver a una copia:  python manage.py restaurar_copia copias/<archivo>.zip --confirmar

La base de datos se copia con la función «backup» de SQLite: aunque alguien esté usando la página
en ese momento, la copia queda completa y sin errores. Las miniaturas no se copian (se vuelven a crear solas).
"""

import os
import re
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.utils import timezone

DIAS_GUARDADAS = 14
PATRON_NOMBRE = re.compile(r"^nexalys-copia-\d{8}-\d{6}\.zip$")
LEEME = """Copia de seguridad de NEXALYS Tec ({fecha}).

Contiene:
  db.sqlite3  -> la base de datos completa (cuentas, tiendas, productos, ventas, ...)
  media/      -> las fotos de los productos y los logos de las tiendas

Para volver a esta copia (con la página detenida):
  python manage.py restaurar_copia copias/{nombre} --confirmar
"""


def carpeta():
    destino = Path(getattr(settings, "COPIAS_CARPETA", "") or Path(settings.BASE_DIR) / "copias")
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def listar():
    """Copias guardadas, de la más nueva a la más antigua: [{nombre, ruta, tamano, fecha}]."""
    copias = []
    for ruta in carpeta().iterdir():
        if ruta.is_file() and PATRON_NOMBRE.match(ruta.name):
            info = ruta.stat()
            copias.append({
                "nombre": ruta.name,
                "ruta": ruta,
                "tamano": info.st_size,
                "fecha": timezone.localtime(datetime.fromtimestamp(info.st_mtime, tz=timezone.get_current_timezone())),
            })
    return sorted(copias, key=lambda c: c["nombre"], reverse=True)


def buscar(nombre):
    """La copia con ese nombre exacto, o None (así nadie puede pedir otro archivo del servidor)."""
    if not PATRON_NOMBRE.match(nombre or ""):
        return None
    ruta = carpeta() / nombre
    return ruta if ruta.is_file() else None


def _copiar_base_de_datos(destino):
    if connection.vendor != "sqlite":
        raise RuntimeError("Las copias automáticas solo funcionan con SQLite.")
    connection.ensure_connection()
    with sqlite3.connect(destino) as copia:
        connection.connection.backup(copia)
    copia.close()


def crear():
    """Crea una copia nueva y borra las viejas. Devuelve el dict de la copia creada."""
    ahora = timezone.localtime()
    nombre = f"nexalys-copia-{ahora:%Y%m%d-%H%M%S}.zip"
    destino = carpeta() / nombre
    temporal = destino.with_suffix(".zip.tmp")
    media = Path(settings.MEDIA_ROOT)
    with tempfile.TemporaryDirectory() as trabajo:
        base = Path(trabajo) / "db.sqlite3"
        _copiar_base_de_datos(base)
        with zipfile.ZipFile(temporal, "w") as archivo:
            archivo.writestr("LEEME.txt", LEEME.format(fecha=f"{ahora:%d/%m/%Y %H:%M}", nombre=nombre))
            archivo.write(base, "db.sqlite3", compress_type=zipfile.ZIP_DEFLATED)
            if media.is_dir():
                for ruta in sorted(media.rglob("*")):
                    relativa = ruta.relative_to(media)
                    if ruta.is_file() and relativa.parts[0] != "miniaturas":
                        # Las fotos ya están comprimidas (WEBP): se guardan tal cual, más rápido.
                        archivo.write(ruta, f"media/{relativa.as_posix()}", compress_type=zipfile.ZIP_STORED)
    os.replace(temporal, destino)  # el .zip aparece completo de una vez
    borrar_viejas()
    return next(c for c in listar() if c["nombre"] == nombre)


def borrar_viejas():
    """Borra las copias de más de DIAS_GUARDADAS días, pero nunca la más reciente."""
    limite = timezone.now() - timedelta(days=DIAS_GUARDADAS)
    borradas = 0
    for copia in listar()[1:]:
        if copia["fecha"] < limite:
            copia["ruta"].unlink(missing_ok=True)
            borradas += 1
    return borradas


def restaurar(ruta_zip):
    """
    Vuelve a la copia: reemplaza la base de datos y copia las fotos. Antes guarda la base actual
    como db.sqlite3.antes-de-restaurar por si hiciera falta. Solo con la página detenida.
    """
    ruta_zip = Path(ruta_zip)
    with zipfile.ZipFile(ruta_zip) as archivo:
        nombres = archivo.namelist()
        if "db.sqlite3" not in nombres:
            raise ValueError("Ese archivo no es una copia de NEXALYS Tec (no tiene db.sqlite3).")
        base = Path(settings.DATABASES["default"]["NAME"])
        connection.close()
        if base.exists():
            os.replace(base, base.with_name(base.name + ".antes-de-restaurar"))
        with archivo.open("db.sqlite3") as origen, open(base, "wb") as destino:
            destino.write(origen.read())
        media = Path(settings.MEDIA_ROOT).resolve()
        fotos = 0
        for nombre in nombres:
            if not nombre.startswith("media/") or nombre.endswith("/"):
                continue
            destino = (media / nombre.removeprefix("media/")).resolve()
            if media not in destino.parents:  # nunca escribir fuera de media/
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            with archivo.open(nombre) as origen, open(destino, "wb") as salida:
                salida.write(origen.read())
            fotos += 1
    return fotos
