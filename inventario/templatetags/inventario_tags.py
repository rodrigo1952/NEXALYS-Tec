from django import template

from inventario.reportes import cantidad_de_alertas

register = template.Library()


@register.simple_tag
def alertas_inventario(tienda):
    """Cuántos productos de la tienda están agotados o con stock bajo (para el menú)."""
    return cantidad_de_alertas(tienda) if tienda is not None else 0
