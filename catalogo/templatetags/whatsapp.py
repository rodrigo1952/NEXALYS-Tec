"""
Enlaces de WhatsApp con el mensaje armado para quien está viendo la página (catalogo/whatsapp.py):

  {% load whatsapp %}
  <a href="{% whatsapp_producto producto %}">…   <a href="{% whatsapp_tienda tienda %}">…
"""

from django import template

register = template.Library()


def _usuario(context):
    request = context.get("request")
    return getattr(request, "user", None)


@register.simple_tag(takes_context=True)
def whatsapp_producto(context, producto):
    return producto.enlace_whatsapp(_usuario(context))


@register.simple_tag(takes_context=True)
def whatsapp_tienda(context, tienda):
    return tienda.enlace_whatsapp_consulta(_usuario(context))
