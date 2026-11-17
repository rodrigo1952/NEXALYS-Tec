"""
Mensajes que se escriben solos al tocar un botón de WhatsApp (el cliente puede cambiarlos antes de enviar).

  Buenas tardes, Selva Byte. Soy David. Vi este producto en NEXALYS Tec:

  *Samsung Galaxy A26 5G 128GB 6GB RAM Negro*
  Precio: S/ 1,199.00

  ¿Sigue disponible? ¿Cómo puedo comprarlo?

  https://…/catalogo/producto/10/

- El saludo depende de la hora de Perú: Buenos días (5:00 a 11:59), Buenas tardes (12:00 a 18:59), Buenas noches.
- «Soy David.» solo si inició sesión y tiene nombre (nunca el usuario ni el correo).
- *texto* es negrita en WhatsApp.
- El enlace va al final: así WhatsApp le muestra a la tienda la foto, el nombre y el precio.
"""

from django.utils import timezone


def saludo(momento=None):
    hora = timezone.localtime(momento).hour
    if 5 <= hora < 12:
        return "Buenos días"
    if 12 <= hora < 19:
        return "Buenas tardes"
    return "Buenas noches"


def _presentacion(usuario):
    nombre = (getattr(usuario, "first_name", "") or "").strip() if getattr(usuario, "is_authenticated", False) else ""
    return f" Soy {nombre.split()[0]}." if nombre else ""


def _inicio(tienda, usuario):
    return f"{saludo()}, {tienda.nombre}.{_presentacion(usuario)}"


def _negrita(texto):
    return "*" + texto.replace("*", "") + "*"


def mensaje_producto(producto, usuario=None):
    from .templatetags.formato import soles

    nombre = _negrita(producto.nombre)
    if producto.agotado:
        return (
            f"{_inicio(producto.tienda, usuario)} Vi este producto en NEXALYS Tec y aparece agotado:\n\n"
            f"{nombre}\n\n"
            "¿Saben cuándo vuelve a tener stock?\n\n"
            f"{producto.enlace_publico()}"
        )
    return (
        f"{_inicio(producto.tienda, usuario)} Vi este producto en NEXALYS Tec:\n\n"
        f"{nombre}\nPrecio: {soles(producto.precio_final)}\n\n"
        "¿Sigue disponible? ¿Cómo puedo comprarlo?\n\n"
        f"{producto.enlace_publico()}"
    )


def mensaje_tienda(tienda, usuario=None):
    return (
        f"{_inicio(tienda, usuario)} Encontré su tienda en NEXALYS Tec y quisiera hacerles una consulta.\n\n"
        f"{tienda.enlace_publico()}"
    )
