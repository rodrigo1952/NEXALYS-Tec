from django import template

from catalogo.imagenes import url_miniatura

register = template.Library()


@register.filter
def miniatura(imagen, tipo="tarjeta"):
    """
    Copia chica de una foto (pesa mucho menos).
    {{ producto.imagen|miniatura }}            → 600 px, para tarjetas
    {{ producto.imagen|miniatura:"icono" }}    → 160 px, para miniaturas pequeñas
    {{ producto.imagen|miniatura:"compartir" }} → JPEG de 600 px, para la vista previa en WhatsApp
    """
    return url_miniatura(imagen, tipo)
