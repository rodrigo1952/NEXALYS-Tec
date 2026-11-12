"""
Código QR de la tienda: lleva a su página en NEXALYS Tec (enlace completo con SITIO_URL).
Lo genera la librería segno (pura Python, licencia BSD). Nivel de corrección «Q»: se sigue leyendo
aunque el cartel esté un poco sucio o arrugado.
"""

import io

import segno

AZUL_MARINO = "#0B1B3A"


def crear(tienda):
    return segno.make(tienda.enlace_publico(), error="q")


def svg(tienda):
    """SVG para mostrar dentro de la página (se agranda sin perder nitidez)."""
    return crear(tienda).svg_inline(scale=10, border=2, dark=AZUL_MARINO, omitsize=True)


def archivo(tienda, formato):
    """Bytes del QR para descargar: «png» (para WhatsApp o Word) o «svg» (para imprenta)."""
    salida = io.BytesIO()
    if formato == "png":
        crear(tienda).save(salida, kind="png", scale=16, border=4, dark=AZUL_MARINO)
    else:
        crear(tienda).save(salida, kind="svg", scale=16, border=4, dark=AZUL_MARINO, xmldecl=True)
    return salida.getvalue()
