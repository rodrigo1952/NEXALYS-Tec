"""
Color de la etiqueta de cada marca (nov 2026). Lo elige el administrador al crear o editar la marca.

La etiqueta lleva el nombre en blanco, así que el color debe ser lo bastante oscuro para que se lea:
se pide un contraste de al menos 4.5 : 1 (la norma WCAG AA para texto pequeño).
"""

from django.core.validators import RegexValidator

COLOR_MARCA_POR_DEFECTO = "#0B1B3A"  # azul marino de NEXALYS
CONTRASTE_MINIMO = 4.5
PATRON_COLOR = r"^#[0-9A-Fa-f]{6}$"

validar_color = RegexValidator(PATRON_COLOR, "Escribe el color como #RRGGBB (por ejemplo #1428A0).")


def _canal(valor):
    valor /= 255
    return valor / 12.92 if valor <= 0.03928 else ((valor + 0.055) / 1.055) ** 2.4


def luminancia(color):
    """Luminancia relativa de un color #RRGGBB (0 = negro, 1 = blanco)."""
    rojo, verde, azul = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _canal(rojo) + 0.7152 * _canal(verde) + 0.0722 * _canal(azul)


def contraste_con_blanco(color):
    """Contraste entre el texto blanco y el color de fondo (de 1 a 21)."""
    return 1.05 / (luminancia(color) + 0.05)
