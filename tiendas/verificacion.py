"""
Verificación de tiendas por correo electrónico.

Se genera un enlace firmado (no se guarda nada en la base de datos): Django firma
el id de la tienda con la SECRET_KEY, así nadie puede fabricar un enlace válido.
El enlace vence a las VERIFICACION_TIENDA_HORAS horas.
"""

import logging

from django.conf import settings
from django.core import signing
from django.urls import reverse

from config import correos
from cuentas import codigos

logger = logging.getLogger(__name__)

SAL = "tiendas.verificacion-correo"


def horas_validez():
    return getattr(settings, "VERIFICACION_TIENDA_HORAS", 24)


def generar_token(tienda):
    return signing.dumps({"tienda": tienda.pk}, salt=SAL)


def leer_token(token):
    """Devuelve el id de la tienda, o None si el enlace es inválido o venció."""
    try:
        datos = signing.loads(token, salt=SAL, max_age=horas_validez() * 3600)
    except signing.BadSignature:  # también cubre SignatureExpired
        return None
    if not isinstance(datos, dict):
        return None
    return datos.get("tienda")


def enviar_correo_verificacion(request, tienda):
    """Correo con el botón «Verificar mi tienda» y un código de 6 dígitos (cuentas/codigos.py)."""
    enlace = correos.enlace(reverse("tiendas:verificar", args=[generar_token(tienda)]), request)
    codigo = codigos.nuevo(tienda.usuario)
    correos.enviar(
        [tienda.usuario.email], "Verifica tu tienda en NEXALYS Tec", "tiendas/correo_verificacion",
        {"tienda": tienda, "enlace": enlace, "codigo": codigo, "vence": correos.vence_en_palabras(horas_validez())},
        vista_previa=f"Activa {tienda.nombre} con un toque o con el código {codigo[:3]} {codigo[3:]}.",
    )
    if settings.DEBUG:
        print(f"\n[NEXALYS] Enlace de verificación para {tienda.usuario.email}:\n{enlace}\nCódigo: {codigo}\n")


def enviar_bienvenida(request, tienda):
    """Al verificar la tienda: bienvenida con los primeros pasos. Si el correo falla, solo se anota."""
    try:
        correos.enviar(
            [tienda.usuario.email], f"{tienda.nombre} ya está activa en NEXALYS Tec", "tiendas/correo_bienvenida",
            {"tienda": tienda, "enlace": correos.enlace(reverse("tiendas:panel"), request)},
            vista_previa="Tu tienda ya está activa. Estos son tus primeros pasos.",
        )
    except Exception:
        logger.exception("No se pudo enviar el correo de bienvenida de la tienda")
