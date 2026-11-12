from django import template

from reclamos.models import Reclamo

register = template.Library()


@register.simple_tag
def reclamos_pendientes(tienda=None, todas=False):
    """Hojas sin responder: de una tienda, o todas (para el globito de la consola)."""
    pendientes = Reclamo.objects.filter(estado=Reclamo.Estado.PENDIENTE)
    if todas:
        return pendientes.count()
    if tienda is None:
        return 0
    return pendientes.filter(tienda=tienda).count()
