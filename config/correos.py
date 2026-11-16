"""
Correos de NEXALYS Tec con un mismo diseño profesional.

Cada correo tiene dos versiones de la misma plantilla:
  <ruta>.html  → la que ve casi todo el mundo (Gmail, Outlook…): encabezado azul marino, botón y pie.
                 Extiende templates/correos/base.html.
  <ruta>.txt   → texto simple, para programas de correo que no muestran diseño (y ayuda a no caer en spam).

  enviar(["cliente@correo.com"], "Asunto", "cuentas/correo_confirmacion", {...}, vista_previa="…")

- Los enlaces se arman con SITIO_URL (https en el servidor o en el túnel), no con la dirección de la visita.
- «Responder» va a CORREO_SOPORTE (si está en el .env), no a la cuenta que envía.
- vence_en_palabras(24) → «el lunes 16 de noviembre a las 5:24 p. m.»
"""

from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]


def enlace(ruta, request=None):
    """Dirección completa para un correo: SITIO_URL + ruta. Sin SITIO_URL, la de la visita."""
    base = (getattr(settings, "SITIO_URL", "") or "").rstrip("/")
    if base:
        return base + ruta
    if request is not None:
        return request.build_absolute_uri(ruta)
    return ruta


def hora_en_palabras(momento):
    """5:24 p. m. · 12:05 p. m. · 9:00 a. m."""
    hora = momento.hour % 12 or 12
    return f"{hora}:{momento.minute:02d} {'a. m.' if momento.hour < 12 else 'p. m.'}"


def fecha_en_palabras(momento):
    """«el lunes 16 de noviembre a las 5:24 p. m.» (hora de Perú)."""
    momento = timezone.localtime(momento)
    articulo = "la" if momento.hour % 12 == 1 else "las"
    return (f"el {DIAS[momento.weekday()]} {momento.day} de {MESES[momento.month - 1]} "
            f"a {articulo} {hora_en_palabras(momento)}")


def vence_en_palabras(horas):
    return fecha_en_palabras(timezone.now() + timedelta(hours=horas))


def _contexto_base():
    return {
        "sitio_url": (getattr(settings, "SITIO_URL", "") or "").rstrip("/"),
        "correo_soporte": getattr(settings, "CORREO_RESPUESTAS", ""),
        "anio": timezone.localdate().year,
    }


def enviar(destinos, asunto, plantilla, contexto=None, *, vista_previa=""):
    """
    Envía un correo con las dos versiones (HTML y texto). Si el servidor de correo falla, lanza el error:
    quien llama decide qué hacer (normalmente avisar en la página y anotarlo en Control → Errores).
    """
    destinos = [d for d in destinos if d]
    if not destinos:
        return False
    datos = {**_contexto_base(), **(contexto or {}), "asunto": asunto, "vista_previa": vista_previa}
    texto = render_to_string(f"{plantilla}.txt", datos)
    html = render_to_string(f"{plantilla}.html", datos)
    respuestas = getattr(settings, "CORREO_RESPUESTAS", "")
    mensaje = EmailMultiAlternatives(asunto, texto, None, destinos, reply_to=[respuestas] if respuestas else None)
    mensaje.attach_alternative(html, "text/html")
    mensaje.send()
    return True
