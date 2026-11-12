"""
Protección de datos personales (Ley N.° 29733 y su reglamento, D.S. 016-2024-JUS).

  - VERSION_POLITICA: fecha de la política vigente. Si cambias el texto de la política
    (templates/cuentas/privacidad.html), cambia esta fecha: todos deberán aceptarla de nuevo al entrar.
  - Los datos del responsable (titular del banco de datos) van en el .env: PRIVACIDAD_TITULAR, ...
    Mientras falten, la consola del administrador lo avisa en «Tareas pendientes».
  - Plazos para responder los derechos, en días hábiles (lunes a viernes).
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

VERSION_POLITICA = "2026-11-11"
CLAVE_SESION = "privacidad_aceptada"

# Datos del responsable: nombre del .env → texto que se muestra en la política.
DATOS_TITULAR = {
    "PRIVACIDAD_TITULAR": "Responsable (nombre o razón social)",
    "PRIVACIDAD_DOCUMENTO": "DNI o RUC",
    "PRIVACIDAD_DIRECCION": "Domicilio",
    "PRIVACIDAD_CORREO": "Correo para tus derechos",
    "PRIVACIDAD_BANCO_DATOS": "Banco de datos y código de inscripción",
    "PRIVACIDAD_SERVIDOR": "Dónde está el servidor",
}

# Plazos máximos para responder (días hábiles), según el reglamento.
PLAZOS = {"informacion": 8, "acceso": 20, "rectificacion": 10, "cancelacion": 10, "oposicion": 10}


def datos_titular():
    """{"PRIVACIDAD_TITULAR": "…", …}: lo que dice el .env (vacío si falta)."""
    return {nombre: getattr(settings, nombre, "") for nombre in DATOS_TITULAR}


def datos_faltantes():
    """Nombres de los datos del responsable que todavía no están en el .env."""
    return [DATOS_TITULAR[nombre] for nombre, valor in datos_titular().items() if not valor]


def sumar_dias_habiles(desde, dias):
    """Fecha límite contando solo de lunes a viernes (los feriados no se descuentan)."""
    fecha = desde
    while dias > 0:
        fecha += timedelta(days=1)
        if fecha.weekday() < 5:
            dias -= 1
    return fecha


def exento(usuario):
    """El equipo de administración trabaja para el responsable: no se le pide aceptar la política."""
    return usuario.is_superuser or usuario.groups.filter(name="Administrador").exists()


def acepto_version_vigente(request):
    if request.session.get(CLAVE_SESION) == VERSION_POLITICA:
        return True
    from .models import ConsentimientoPrivacidad

    if ConsentimientoPrivacidad.objects.filter(usuario=request.user, version=VERSION_POLITICA).exists():
        request.session[CLAVE_SESION] = VERSION_POLITICA
        return True
    return False


def registrar_aceptacion(request, usuario, origen):
    """Guarda la prueba del consentimiento: quién, qué versión, cuándo, desde dónde y en qué formulario."""
    from .limites import ip_de
    from .models import ConsentimientoPrivacidad

    ConsentimientoPrivacidad.objects.create(
        usuario=usuario, version=VERSION_POLITICA, origen=origen, ip=ip_de(request), fecha=timezone.now(),
    )
    if getattr(request, "user", None) == usuario:
        request.session[CLAVE_SESION] = VERSION_POLITICA
