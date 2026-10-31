"""
Claves temporales: el administrador restablece la contraseña de un cliente o una tienda.

La clave se genera al azar, se muestra UNA vez al administrador (para que se la pase a la
persona) y nunca se guarda. Vence en 24 horas y, al entrar con ella, la persona debe crear
su propia contraseña antes de seguir (ver middleware.ClaveTemporalMiddleware).
"""

import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import ClaveTemporal

HORAS_CLAVE_TEMPORAL = 24
CLAVE_SESION = "debe_cambiar_clave"
# Sin letras ni números que se confunden al dictarlos (0/O, 1/l/I).
LETRAS = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generar_clave():
    """Ej.: «Kp7m-Q2xr-9WaT» (12 caracteres al azar, en grupos de 4 para dictarla fácil)."""
    return "-".join("".join(secrets.choice(LETRAS) for _ in range(4)) for _ in range(3))


def restablecer(usuario):
    """Pone una clave temporal nueva a la cuenta y la devuelve (para mostrarla una sola vez)."""
    clave = generar_clave()
    ahora = timezone.now()
    with transaction.atomic():
        usuario.set_password(clave)  # cambia el cifrado: cierra sus sesiones abiertas en otros equipos
        usuario.save(update_fields=["password"])
        ClaveTemporal.objects.update_or_create(
            usuario=usuario,
            defaults={"creada": ahora, "vence": ahora + timedelta(hours=HORAS_CLAVE_TEMPORAL), "huella": usuario.password},
        )
    return clave, ahora + timedelta(hours=HORAS_CLAVE_TEMPORAL)


def vigente(usuario):
    """La clave temporal de la cuenta si sigue puesta (vencida o no); si ya la cambió, la borra y devuelve None."""
    registro = ClaveTemporal.objects.filter(usuario=usuario).select_related("usuario").first()
    if registro is None:
        return None
    if not registro.sigue_puesta():
        registro.delete()
        return None
    return registro
