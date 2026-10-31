"""
Destacados del Inicio repartidos por TURNOS entre las tiendas.

Cada tienda puede destacar hasta 3 productos, pero en el Inicio solo hay 8 lugares. Para que
ninguna tienda acapare la sección (ni quede siempre fuera):
  1. Primera vuelta: entra 1 producto de cada tienda (su destacado más popular).
  2. Segunda vuelta: el 2.º de cada tienda; luego el 3.º… hasta llenar los 8 lugares.
  3. El orden de las tiendas en cada vuelta ROTA cada día: la que hoy va primero, mañana va última.
Dentro de cada tienda manda la popularidad de los últimos 30 días (vistas + favoritos × 5).
Todos los destacados se pueden ver en el catálogo con «Ver todos los destacados».
"""

from django.utils import timezone

LUGARES_EN_INICIO = 8


def destacados_en_turnos(visibles, cantidad=LUGARES_EN_INICIO, hoy=None):
    """Devuelve (productos para el Inicio, total de destacados)."""
    por_tienda = {}
    for producto in visibles.destacados_inicio():  # ya vienen del más popular al menos popular
        por_tienda.setdefault(producto.tienda_id, []).append(producto)
    total = sum(len(lista) for lista in por_tienda.values())
    if not por_tienda:
        return [], 0

    tiendas = sorted(por_tienda)
    hoy = hoy or timezone.localdate()
    giro = hoy.toordinal() % len(tiendas)
    tiendas = tiendas[giro:] + tiendas[:giro]  # turno del día

    elegidos = []
    vuelta = 0
    while len(elegidos) < cantidad and any(len(por_tienda[t]) > vuelta for t in tiendas):
        for tienda in tiendas:
            if len(por_tienda[tienda]) > vuelta and len(elegidos) < cantidad:
                elegidos.append(por_tienda[tienda][vuelta])
        vuelta += 1
    return elegidos, total
