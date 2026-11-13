"""
Con DEBUG=True (tu PC), Django muestra los errores con todos sus detalles (la página amarilla): rutas de tu PC,
variables del sistema, la dirección secreta del admin… Sirve para programar, pero no debe verla nadie más.

Si la visita NO viene de tu propia PC (por ejemplo, un cliente que entra por el enlace del túnel de Cloudflare
o un celular por el Wi-Fi), esa página se cambia por la página de error normal de NEXALYS (404, 403 o 500),
sin datos técnicos. En tu PC (localhost o 127.0.0.1) se sigue viendo el detalle.
El error igual queda anotado: en la terminal de runserver y en Control → Errores.

Con DEBUG=False (servidor) no hace nada: Django ya muestra las páginas normales.
"""

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader

# Todas las páginas de detalle de Django (error 500, 404 con la lista de direcciones, CSRF) llevan esta línea.
MARCA_PAGINA_TECNICA = b'<meta name="robots" content="NONE,NOARCHIVE">'
TU_PC = {"localhost", "127.0.0.1", "[::1]"}


def es_visita_de_tu_pc(request):
    """True si se abrió en tu misma PC. No usa request.get_host(), que falla justo cuando el dominio no está permitido."""
    if "HTTP_CF_CONNECTING_IP" in request.META:  # llegó por el túnel de Cloudflare
        return False
    host = request.META.get("HTTP_HOST", "")
    host = host.rsplit(":", 1)[0] if not host.endswith("]") else host
    return host in TU_PC


def es_pagina_tecnica(respuesta):
    return (
        respuesta.status_code >= 400
        and not getattr(respuesta, "streaming", False)
        and respuesta.get("Content-Type", "").startswith("text/html")
        and MARCA_PAGINA_TECNICA in respuesta.content
    )


def pagina_normal(request, codigo):
    if codigo in (403, 404):
        try:
            return render(request, f"{codigo}.html", status=codigo)
        except Exception:  # noqa: BLE001 — si la plantilla con diseño falla, queda la página simple de abajo
            pass
    # 500.html no usa datos de la visita: se muestra aunque falle todo lo demás.
    return HttpResponse(loader.get_template("500.html").render(), status=codigo)


class OcultarDetallesFueraDeTuPC:
    """Va primero en MIDDLEWARE para revisar la respuesta final, venga de donde venga el error."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        if settings.DEBUG and es_pagina_tecnica(respuesta) and not es_visita_de_tu_pc(request):
            nueva = pagina_normal(request, respuesta.status_code)
            for cabecera in ("Content-Security-Policy", "X-Frame-Options"):
                if cabecera in respuesta:
                    nueva[cabecera] = respuesta[cabecera]
            return nueva
        return respuesta
