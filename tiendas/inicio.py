"""
Bloque «¿Qué tienda está abierta ahora?» del Inicio (estilo «Carbón y oro», nov 2026).

Hasta 6 tiendas activas: primero las que tienen el local abierto, luego las cerradas o en refrigerio y al final
las que no registraron su horario; dentro de cada grupo, de la A a la Z. El resto está en «Tiendas cercanas».
Cada tarjeta lleva hasta 3 etiquetas (tiendas/etiquetas.py) y 3 productos con stock (destacados primero).
Toda la tarjeta lleva al perfil de la tienda (ahí están WhatsApp, Cómo llegar y sus productos).
"""

import unicodedata

from .etiquetas import especialidades_por_tienda, etiquetas
from .models import Tienda

LIMITE_INICIO = 6
PRODUCTOS_POR_TIENDA = 3
ETIQUETAS_POR_TIENDA = 3


def _primera_minuscula(texto):
    return texto[:1].lower() + texto[1:] if texto else ""


def etiqueta_estado(estado):
    """Texto corto de la etiqueta: «Abierto ahora · cierra a las 7:00 p. m.», «Cerrado · abre a las 9:00 a. m.»."""
    if not estado:
        return ""
    if estado["abierto"]:
        return f"Abierto ahora · {_primera_minuscula(estado['detalle'])}"
    if estado["refrigerio"]:
        return f"En refrigerio · {_primera_minuscula(estado['detalle'])}"
    return f"Cerrado · {_primera_minuscula(estado['detalle'])}"


def _clave_nombre(nombre):
    """«Épsilon» junto a «Eta» (sin tildes ni mayúsculas), no al final como en SQLite."""
    return unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().lower()


def tiendas_para_inicio(limite=LIMITE_INICIO):
    """Devuelve (lista de tiendas para las tarjetas, total de tiendas activas)."""
    tiendas = list(
        Tienda.objects.filter(estado=Tienda.Estado.ACTIVA).prefetch_related("horarios")
    )
    lista = []
    for tienda in tiendas:
        estado = tienda.estado_atencion()
        grupo = 2 if estado is None else (0 if estado["abierto"] else 1)
        lista.append({
            "tienda": tienda,
            "inicial": tienda.nombre[:1].upper(),
            "abierto": estado["abierto"] if estado else None,
            "estado": etiqueta_estado(estado),
            "grupo": grupo,
        })
    lista.sort(key=lambda t: (t["grupo"], _clave_nombre(t["tienda"].nombre)))
    elegidas = lista[:limite]
    especialidades = especialidades_por_tienda(t["tienda"].pk for t in elegidas)
    for t in elegidas:
        t["etiquetas"] = etiquetas(t["tienda"], especialidades.get(t["tienda"].pk, []), maximo=ETIQUETAS_POR_TIENDA)
        t["productos"] = productos_de_muestra(t["tienda"])
    return elegidas, len(tiendas)


def productos_de_muestra(tienda, cantidad=PRODUCTOS_POR_TIENDA):
    """Productos publicados y con stock: primero los destacados, luego los más nuevos."""
    from catalogo.models import Producto  # aquí para no crear un import circular

    return list(
        Producto.objects.visibles().filter(tienda=tienda, stock__gt=0).order_by("-destacado", "-creado")[:cantidad]
    )
