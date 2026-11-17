from django.conf import settings


def sitio(request):
    """Dirección pública del sitio (SITIO_URL del .env) para armar enlaces completos en las plantillas
    y el correo de soporte (CORREO_SOPORTE del .env) que se muestra en el pie de página."""
    return {"SITIO_URL": settings.SITIO_URL, "correo_soporte": settings.CORREO_SOPORTE}


def enlace_completo(ruta):
    """/catalogo/producto/10/ → https://tu-dominio.com/catalogo/producto/10/"""
    return settings.SITIO_URL + ruta
