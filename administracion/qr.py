"""
QR de la página de NEXALYS Tec (consola del administrador → General → «QR de la página»).

Para ferias, presentaciones y carteles: lleva al Inicio con la marca «?desde=qr», y así se cuentan las
visitas que llegan escaneándolo (modelo VisitaQR, solo la fecha: ningún dato de la persona).

El enlace sale de SITIO_URL (.env). Con el túnel de Cloudflare ese enlace cambia cada vez que se abre,
por eso el QR NO se guarda: se arma de nuevo cada vez que se abre la página o la pantalla para la feria.
Lo genera segno (como el QR de las tiendas, tiendas/qr.py), con corrección «Q».
"""

import io
from datetime import datetime, time
from urllib.parse import urlparse

import segno
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

AZUL_MARINO = "#0B1B3A"
MARCA = "qr"                    # lo que va en ?desde=
CLAVE_SESION = "vino_por_qr"    # cada persona (sesión) cuenta una sola vez


def enlace():
    return f"{settings.SITIO_URL}{reverse('inicio')}?desde={MARCA}"


def enlace_corto():
    """Lo que se lee bajo el QR: solo el dominio (p. ej. «abc-def.trycloudflare.com»)."""
    return urlparse(settings.SITIO_URL).netloc or settings.SITIO_URL or "esta computadora"


def es_local():
    """True si el QR solo funcionaría en esta PC (SITIO_URL vacío o con localhost / 127.0.0.1)."""
    sitio = settings.SITIO_URL
    return not sitio.startswith("http") or "127.0.0.1" in sitio or "localhost" in sitio


def crear():
    return segno.make(enlace(), error="q")


def svg():
    """SVG para mostrar dentro de la página (se agranda sin perder nitidez)."""
    return crear().svg_inline(scale=10, border=2, dark=AZUL_MARINO, omitsize=True)


def archivo(formato):
    """Bytes del QR para descargar: «png» o «svg» (para imprenta)."""
    salida = io.BytesIO()
    if formato == "png":
        crear().save(salida, kind="png", scale=16, border=4, dark=AZUL_MARINO)
    else:
        crear().save(salida, kind="svg", scale=16, border=4, dark=AZUL_MARINO, xmldecl=True)
    return salida.getvalue()


def registrar_visita(request):
    """
    Suma una visita por el QR. Cada persona cuenta una vez (se anota en su sesión) y no cuenta el
    administrador probando su propio QR. Devuelve True si la contó.
    """
    from cuentas.views import tiene_rol

    from .models import VisitaQR

    if request.session.get(CLAVE_SESION) or tiene_rol(request.user, "Administrador"):
        return False
    VisitaQR.objects.create()
    request.session[CLAVE_SESION] = True
    return True


def resumen_visitas():
    from .models import VisitaQR

    inicio_hoy = timezone.make_aware(datetime.combine(timezone.localdate(), time.min))
    visitas = VisitaQR.objects.all()
    return {
        "total": visitas.count(),
        "hoy": visitas.filter(fecha__gte=inicio_hoy).count(),
        "ultima": visitas.order_by("-fecha").values_list("fecha", flat=True).first(),
    }
