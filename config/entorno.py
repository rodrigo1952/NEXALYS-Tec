"""
Lee los datos secretos y los ajustes del servidor desde el archivo .env (junto a manage.py).

El archivo .env NO se sube a GitHub (está en .gitignore): cada PC y el servidor tienen el suyo.
Formato: una línea por dato, NOMBRE=valor. Las líneas que empiezan con # son comentarios.
Lo que diga el .env manda: si VS Code (o el sistema) ya puso un valor viejo en la terminal, el .env lo reemplaza.
Así, al cambiar el .env basta con reiniciar runserver. Un dato que NO está en el .env se toma del sistema.

Para crear un .env nuevo con una clave secreta al azar:  python config/crear_env.py
Modelo con todos los datos y su explicación: .env.example
"""

import os


def cargar_env(ruta):
    """Copia los datos del .env a os.environ (reemplaza los que ya existan). Si no hay .env, no hace nada."""
    try:
        with open(ruta, encoding="utf-8") as archivo:
            lineas = archivo.read().splitlines()
    except FileNotFoundError:
        return
    for linea in lineas:
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        nombre, valor = linea.split("=", 1)
        nombre, valor = nombre.strip(), valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]  # NOMBRE="valor" o NOMBRE='valor'
        os.environ[nombre] = valor


def texto(nombre, por_defecto=""):
    return os.environ.get(nombre, por_defecto).strip()


def si_o_no(nombre, por_defecto=False):
    """True con 1, true, si, sí, yes u on (sin importar mayúsculas)."""
    valor = texto(nombre)
    if not valor:
        return por_defecto
    return valor.lower() in ("1", "true", "si", "sí", "yes", "on")


def lista(nombre, por_defecto=None):
    """Varios valores separados por comas: a.com, b.com → ["a.com", "b.com"]."""
    valor = texto(nombre)
    if not valor:
        return list(por_defecto or [])
    return [parte.strip() for parte in valor.split(",") if parte.strip()]


def entero(nombre, por_defecto):
    valor = texto(nombre)
    return int(valor) if valor else por_defecto
