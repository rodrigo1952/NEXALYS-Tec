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
