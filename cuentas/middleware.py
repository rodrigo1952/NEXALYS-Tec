from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

from .clave_temporal import CLAVE_SESION


class ClaveTemporalMiddleware:
    """
    Quien entró con una clave temporal debe crear su propia contraseña antes de seguir:
    cualquier página lo lleva a «Crea tu nueva contraseña» (menos esa página y cerrar sesión).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.session.get(CLAVE_SESION):
            permitidas = (reverse("clave_temporal"), reverse("logout"))
            libres = ("/" + settings.STATIC_URL.lstrip("/"), "/" + settings.MEDIA_URL.lstrip("/"))
            if request.path not in permitidas and not request.path.startswith(libres):
                return redirect("clave_temporal")
        return self.get_response(request)
