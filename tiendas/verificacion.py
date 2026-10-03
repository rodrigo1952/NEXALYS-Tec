"""
Verificación de tiendas por correo electrónico.

Se genera un enlace firmado (no se guarda nada en la base de datos): Django firma
el id de la tienda con la SECRET_KEY, así nadie puede fabricar un enlace válido.
El enlace vence a las VERIFICACION_TIENDA_HORAS horas.
"""

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

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
    enlace = request.build_absolute_uri(
        reverse("tiendas:verificar", args=[generar_token(tienda)])
    )
    mensaje = render_to_string(
        "tiendas/correo_verificacion.txt",
        {"tienda": tienda, "enlace": enlace, "horas": horas_validez()},
    )
    send_mail(
        subject="Verifica tu tienda en NEXALYS Tec",
        message=mensaje,
        from_email=None,  # usa DEFAULT_FROM_EMAIL
        recipient_list=[tienda.usuario.email],
    )
    if settings.DEBUG:
        print(f"\n[NEXALYS] Enlace de verificación para {tienda.usuario.email}:\n{enlace}\n")