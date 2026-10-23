"""
Confirmación del correo de los clientes (igual que la verificación de tiendas).

El enlace va firmado con la SECRET_KEY (nadie puede fabricarlo) y vence a las
VERIFICACION_CORREO_HORAS horas. Si vence, el cliente pide uno nuevo.
"""

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

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
    enlace = request.build_absolute_uri(reverse("confirmar_correo", args=[generar_token(usuario)]))
    mensaje = render_to_string(
        "cuentas/correo_confirmacion.txt",
        {"usuario": usuario, "enlace": enlace, "horas": horas_validez()},
    )
    send_mail(
        subject="Confirma tu correo en NEXALYS Tec",
        message=mensaje,
        from_email=None,
        recipient_list=[usuario.email],
    )
    if settings.DEBUG:
        print(f"\n[NEXALYS] Enlace para confirmar el correo de {usuario.email}:\n{enlace}\n")
