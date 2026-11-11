from django.conf import settings


def sitio(request):
    """Dirección pública del sitio (SITIO_URL del .env) para armar enlaces completos en las plantillas."""
    return {"SITIO_URL": settings.SITIO_URL}


def enlace_completo(ruta):
    """/catalogo/producto/10/ → https://tu-dominio.com/catalogo/producto/10/"""
    return settings.SITIO_URL + ruta
