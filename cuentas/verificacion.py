"""
Confirmación del correo de los clientes (igual que la verificación de tiendas).

El enlace va firmado con la SECRET_KEY (nadie puede fabricarlo) y vence a las
VERIFICACION_CORREO_HORAS horas. Si vence, el cliente pide uno nuevo.
"""

import logging

from django.conf import settings
from django.core import signing
from django.urls import reverse

from config import correos

from . import codigos
from .models import DIAS_PARA_CONFIRMAR_CORREO

logger = logging.getLogger(__name__)

SAL = "cuentas.confirmar-correo"


def horas_validez():
    return getattr(settings, "VERIFICACION_CORREO_HORAS", 24)


def generar_token(usuario):
    return signing.dumps({"usuario": usuario.pk}, salt=SAL)


def leer_token(token):
    """Devuelve el id del usuario, o None si el enlace es inválido o venció."""
    try:
        datos = signing.loads(token, salt=SAL, max_age=horas_validez() * 3600)
    except signing.BadSignature:  # también cubre SignatureExpired
        return None
    if not isinstance(datos, dict):
        return None
    return datos.get("usuario")


def enviar_correo_confirmacion(request, usuario):
    """Correo con el botón «Confirmar mi correo» y un código de 6 dígitos (cuentas/codigos.py)."""
    enlace = correos.enlace(reverse("confirmar_correo", args=[generar_token(usuario)]), request)
    codigo = codigos.nuevo(usuario)
    correos.enviar(
        [usuario.email], "Confirma tu correo en NEXALYS Tec", "cuentas/correo_confirmacion",
        {"usuario": usuario, "enlace": enlace, "codigo": codigo, "vence": correos.vence_en_palabras(horas_validez()),
         "dias": DIAS_PARA_CONFIRMAR_CORREO},
        vista_previa=f"Activa tu cuenta con un toque o con el código {codigo[:3]} {codigo[3:]}.",
    )
    if settings.DEBUG:
        print(f"\n[NEXALYS] Enlace para confirmar el correo de {usuario.email}:\n{enlace}\nCódigo: {codigo}\n")


def enviar_bienvenida(request, usuario):
    """Al confirmar el correo: bienvenida con 3 consejos. Si el correo falla, no pasa nada (solo se anota)."""
    try:
        correos.enviar(
            [usuario.email], "Bienvenido a NEXALYS Tec", "cuentas/correo_bienvenida",
            {"usuario": usuario, "enlace": correos.enlace(reverse("catalogo:catalogo"), request)},
            vista_previa="Tu cuenta ya está activa. Así aprovechas NEXALYS Tec.",
        )
    except Exception:
        logger.exception("No se pudo enviar el correo de bienvenida")
