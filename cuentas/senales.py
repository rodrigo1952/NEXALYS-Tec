from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .clave_temporal import CLAVE_SESION, vigente


@receiver(user_logged_in)
def marcar_clave_temporal(sender, request, user, **kwargs):
    """Si entró con una clave temporal, se le pedirá crear su contraseña (ver middleware)."""
    if request is not None and hasattr(request, "session") and vigente(user) is not None:
        request.session[CLAVE_SESION] = True
