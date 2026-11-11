"""
Límite de intentos: frena a quien prueba contraseñas al azar o pide correos sin parar.

Reglas (REGLAS, abajo):
  - Iniciar sesión: 5 contraseñas equivocadas para el MISMO usuario desde la MISMA conexión
    → esa conexión espera 15 minutos para ese usuario. Además, 20 equivocadas desde una misma
    conexión (con cualquier usuario) → espera 15 minutos. El tope por conexión es más alto porque
    en un colegio o una cabina de internet muchas personas comparten la misma IP.
  - Correos (reenviar el enlace de confirmación o verificación y «¿Olvidaste tu contraseña?»):
    3 por hora para el mismo correo o la misma tienda, y 10 por hora desde una misma conexión.

Cuenta el bloqueo desde el intento que completa el límite: si alguien falla 5 veces seguidas,
espera 15 minutos desde la quinta. Mientras espera, sus intentos no se cuentan ni se revisan.
Al entrar bien, se borran sus contraseñas equivocadas (las de ese usuario desde esa conexión).
Los registros de más de un día se borran solos.
"""

import math
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import IntentoAcceso

LOGIN = "login"
CORREO_CONFIRMACION = "confirmacion"
CORREO_TIENDA = "verificacion"
CORREO_CLAVE = "recuperar"

_LOGIN = [(("clave", "ip"), 5, timedelta(minutes=15)), (("ip",), 20, timedelta(minutes=15))]
_CORREO = [(("clave",), 3, timedelta(hours=1)), (("ip",), 10, timedelta(hours=1))]

# acción → lista de (campos que deben coincidir, cantidad máxima, periodo)
REGLAS = {
    LOGIN: _LOGIN,
    CORREO_CONFIRMACION: _CORREO,
    CORREO_TIENDA: _CORREO,
    CORREO_CLAVE: _CORREO,
}


def ip_de(request):
    """IP del visitante. En el hosting puede llegar en otra cabecera (IP_CABECERA del .env)."""
    valor = request.META.get(settings.IP_CABECERA) or request.META.get("REMOTE_ADDR") or ""
    return valor.split(",")[0].strip()[:45]


def _normalizar(clave):
    return (clave or "").strip().lower()[:254]


def _fin_del_bloqueo(fechas, maximo, periodo):
    """
    fechas: intentos de más antiguo a más nuevo. Si en algún tramo hubo «maximo» intentos dentro
    del periodo, el bloqueo dura un periodo completo desde el último de ese tramo.
    """
    fin = None
    for i in range(maximo - 1, len(fechas)):
        if fechas[i] - fechas[i - maximo + 1] <= periodo:
            fin = fechas[i] + periodo
    return fin


def segundos_de_espera(accion, request, clave=""):
    """0 si puede seguir; si no, cuántos segundos le faltan para volver a intentarlo."""
    ahora = timezone.now()
    ip, clave = ip_de(request), _normalizar(clave)
    espera = 0
    for campos, maximo, periodo in REGLAS[accion]:
        filtro = {"accion": accion, "creado__gte": ahora - 2 * periodo}
        if "clave" in campos:
            filtro["clave"] = clave
        if "ip" in campos:
            filtro["ip"] = ip
        fechas = list(IntentoAcceso.objects.filter(**filtro).order_by("creado").values_list("creado", flat=True))
        fin = _fin_del_bloqueo(fechas, maximo, periodo)
        if fin and fin > ahora:
            espera = max(espera, (fin - ahora).total_seconds())
    return math.ceil(espera)


def anotar(accion, request, clave=""):
    """Guarda un intento (contraseña equivocada o correo enviado) y borra los de más de un día."""
    IntentoAcceso.objects.filter(creado__lt=timezone.now() - timedelta(days=1)).delete()
    IntentoAcceso.objects.create(accion=accion, clave=_normalizar(clave), ip=ip_de(request))


def olvidar(accion, request, clave=""):
    """Al entrar bien: se borran las contraseñas equivocadas de ese usuario desde esa conexión."""
    IntentoAcceso.objects.filter(accion=accion, clave=_normalizar(clave), ip=ip_de(request)).delete()


def mensaje_de_espera(segundos):
    minutos = max(1, math.ceil(segundos / 60))
    return f"Demasiados intentos. Vuelve a intentarlo en {minutos} minuto{'s' if minutos != 1 else ''}."
