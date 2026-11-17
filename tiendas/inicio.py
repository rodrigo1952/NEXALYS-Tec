"""
Bloque «¿Qué tienda está abierta ahora?» del Inicio (estilo «Carbón y oro», nov 2026).

Hasta 6 tiendas activas: primero las que tienen el local abierto, luego las cerradas o en refrigerio y al final
las que no registraron su horario; dentro de cada grupo, de la A a la Z. El resto está en «Tiendas cercanas».
"""

import unicodedata

from .models import Tienda

LIMITE_INICIO = 6


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


def tiendas_para_inicio(usuario=None, limite=LIMITE_INICIO):
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
    for t in elegidas:
        t["whatsapp"] = t["tienda"].enlace_whatsapp_consulta(usuario)
    return elegidas, len(tiendas)
