"""Datos pequeños para el menú lateral de la consola de administración."""

from django import template

from tiendas.models import Tienda

from ..models import ErrorRegistrado

register = template.Library()


@register.simple_tag
def tiendas_por_verificar():
    """Cuántas tiendas esperan verificar su correo (se muestra como globito en «Tiendas»)."""
    return Tienda.objects.filter(estado=Tienda.Estado.PENDIENTE).count()


@register.simple_tag
def errores_sin_revisar():
    """Errores de la página que el administrador todavía no revisó (globito en «Errores»)."""
    return ErrorRegistrado.objects.filter(revisado=False).count()


@register.simple_tag
def solicitudes_pendientes():
    """Solicitudes de datos personales sin responder (globito en «Privacidad»)."""
    from cuentas.models import SolicitudDerecho

    return SolicitudDerecho.objects.filter(estado=SolicitudDerecho.Estado.PENDIENTE).count()

