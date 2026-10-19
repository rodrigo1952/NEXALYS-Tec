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
