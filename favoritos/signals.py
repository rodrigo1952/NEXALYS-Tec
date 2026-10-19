"""
"Inicia sesión y se guarda solo": si un visitante tocó el corazón sin haber
iniciado sesión, el id del producto queda en su sesión. Al iniciar sesión
(o al registrarse, porque el registro también inicia sesión) se guarda.
"""

from django.contrib import messages
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from catalogo.models import Producto

from .models import Favorito
from .permisos import es_cliente

CLAVE_SESION = "favorito_pendiente"


@receiver(user_logged_in)
def guardar_favorito_pendiente(sender, request, user, **kwargs):
    if request is None or not hasattr(request, "session"):
        return
    producto_id = request.session.pop(CLAVE_SESION, None)
    if not producto_id:
        return

    if not es_cliente(user):
        messages.info(request, "Solo las cuentas de cliente pueden guardar favoritos.", fail_silently=True)
        return

    producto = Producto.objects.visibles().filter(pk=producto_id).first()
    if producto is None:
        return
    Favorito.guardar(user, producto)
    messages.success(request, f"Guardamos \"{producto.nombre}\" en tus favoritos.", fail_silently=True)
