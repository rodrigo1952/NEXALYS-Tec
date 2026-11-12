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


class PrivacidadMiddleware:
    """
    Quien inició sesión y no aceptó la política de privacidad vigente (cuentas anteriores a la casilla,
    o porque la política cambió) va a «Aceptar la política» antes de seguir. Puede leer la política,
    pedir sus derechos, descargar sus datos, eliminar su cuenta o cerrar sesión sin aceptarla.
    El equipo de administración no la acepta: trabaja para el responsable de los datos.
    """

    LIBRES = (
        "privacidad", "privacidad_aceptar", "privacidad_solicitud", "mis_datos", "eliminar_cuenta",
        "logout", "clave_temporal",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            settings.PRIVACIDAD_OBLIGATORIA
            and request.user.is_authenticated
            and not self._ruta_libre(request.path)
        ):
            from .privacidad import acepto_version_vigente, exento

            if not acepto_version_vigente(request) and not exento(request.user):
                from django.contrib.auth.views import redirect_to_login

                return redirect_to_login(request.get_full_path(), reverse("privacidad_aceptar"))
        return self.get_response(request)

    def _ruta_libre(self, ruta):
        libres = ("/" + settings.STATIC_URL.lstrip("/"), "/" + settings.MEDIA_URL.lstrip("/"))
        if ruta.startswith(libres):
            return True
        return ruta in {reverse(nombre) for nombre in self.LIBRES}
