from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def soles(valor):
    """
    Muestra un precio en soles con separador de miles y 2 decimales.
    Ejemplo: {{ producto.precio|soles }} -> "S/ 2,499.00"
    """
    if valor in (None, ""):
        return ""
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return valor
    return f"S/ {numero:,.2f}"


@register.filter
def correo_oculto(correo):
    """Oculta parte del correo: "diaz1952123@gmail.com" -> "di•••••@gmail.com"."""
    if not correo or "@" not in correo:
        return correo or ""
    usuario, dominio = correo.split("@", 1)
    return f"{usuario[:2]}•••••@{dominio}"


@register.simple_tag
def numeros_de_pagina(pagina, todas_hasta=7):
    """
    Números para la paginación. Con 7 páginas o menos se muestran todas (1 2 3 4 5 6 7);
    con más, la primera, la última y las cercanas a la actual (1 … 5 6 7 8 9 … 30).
    El «…» llega como el texto Paginator.ELLIPSIS.
    """
    paginador = pagina.paginator
    if paginador.num_pages <= todas_hasta:
        return list(paginador.page_range)
    return list(paginador.get_elided_page_range(pagina.number, on_each_side=2, on_ends=1))
