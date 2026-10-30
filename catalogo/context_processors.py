"""
Barra de categorías debajo del menú (en todas las páginas).

- principales: las 5 categorías con MÁS MOVIMIENTO en los últimos 30 días, medido igual que
  los destacados del inicio:  vistas de sus productos + favoritos × 5.
  Si empatan (p. ej. al empezar, sin visitas), primero la que tiene más productos.
  «Otros» no entra entre las principales: siempre va al final de las listas.
- todas: todas las categorías que tienen productos en el catálogo (orden alfabético,
  «Otros» al final), con su cantidad, para el botón «Todas las categorías».

Solo cuentan los productos que el catálogo público muestra (publicados, no ocultos y de
tiendas activas). Se calcula solo cuando la página dibuja la barra.
"""

from datetime import timedelta

from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.functional import SimpleLazyObject

from .models import Categoria, VistaProducto

CANTIDAD_PRINCIPALES = 5
DIAS_MOVIMIENTO = 30
NOMBRE_OTROS = "otros"

VISIBLE = Q(productos__activo=True, productos__oculto_por_admin=False, productos__tienda__estado="activa")


def _contar(consulta):
    """Subconsulta que cuenta filas por categoría (para anotar sin multiplicar los conteos)."""
    return Coalesce(
        Subquery(consulta.order_by().values("producto__categoria").annotate(n=Count("id")).values("n"),
                 output_field=IntegerField()),
        Value(0),
    )


def calcular_categorias():
    from favoritos.models import Favorito  # aquí para no crear un import circular

    desde = timezone.now() - timedelta(days=DIAS_MOVIMIENTO)
    producto_visible = {
        "producto__categoria": OuterRef("pk"), "producto__activo": True,
        "producto__oculto_por_admin": False, "producto__tienda__estado": "activa",
    }
    categorias = list(
        Categoria.objects.filter(activa=True)
        .annotate(
            cantidad=Count("productos", filter=VISIBLE),
            vistas=_contar(VistaProducto.objects.filter(fecha__gte=desde.date(), **producto_visible)),
            favoritos=_contar(Favorito.objects.filter(creado__gte=desde, **producto_visible)),
        )
        .filter(cantidad__gt=0)
    )
    for categoria in categorias:
        categoria.movimiento = categoria.vistas + categoria.favoritos * 5

    candidatas = [c for c in categorias if c.nombre.lower() != NOMBRE_OTROS]
    principales = sorted(candidatas, key=lambda c: (-c.movimiento, -c.cantidad, c.nombre.lower()))
    todas = sorted(categorias, key=lambda c: (c.nombre.lower() == NOMBRE_OTROS, c.nombre.lower()))
    return {"principales": principales[:CANTIDAD_PRINCIPALES], "todas": todas}


def categorias_menu(request):
    return {"menu_categorias": SimpleLazyObject(calcular_categorias)}
