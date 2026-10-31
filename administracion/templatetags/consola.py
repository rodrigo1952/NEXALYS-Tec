"""Datos pequeños para el menú lateral de la consola de administración."""

from django import template

from tiendas.models import Tienda

register = template.Library()


@register.simple_tag
def tiendas_por_verificar():
    """Cuántas tiendas esperan verificar su correo (se muestra como globito en «Tiendas»)."""
    return Tienda.objects.filter(estado=Tienda.Estado.PENDIENTE).count()
