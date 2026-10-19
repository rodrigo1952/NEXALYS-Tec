"""
Búsqueda sin tildes.

SQLite no ignora las tildes: buscar "camara" no encuentra "Cámara". Por eso cada
producto guarda una copia de su texto sin tildes y en minúsculas
(Producto.texto_busqueda) y la búsqueda se hace sobre esa copia.
Funciona igual si más adelante se cambia a MySQL.
"""

import unicodedata


def normalizar(texto):
    """'Cámara  Sony ÑANDÚ' -> 'camara sony nandu'"""
    descompuesto = unicodedata.normalize("NFKD", texto or "")
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return " ".join(sin_tildes.lower().split())
