"""
Aviso de errores: cada vez que una página falla (error 500), se guarda en la base de datos y el
administrador lo ve en la consola (Control → Errores) y en «Tareas pendientes» del Resumen.

Además, Django manda el mismo error por correo a ADMINS (CORREO_ADMIN en el .env) cuando el sitio
está publicado (DEBUG=False) y hay correo real configurado. Sin correo real, queda solo en la consola.

Se conecta en LOGGING (config/settings.py) al registro «django.request», que es donde Django avisa
de los errores 500. Si guardar el error fallara, se ignora: el aviso nunca debe romper la página.
"""

import hashlib
import logging
import traceback

MAXIMO_GUARDADOS = 300  # se conservan los 300 más recientes


def _firma(tipo, marco, ruta):
    return hashlib.sha256(f"{tipo}|{marco}|{ruta}".encode()).hexdigest()


def guardar(registro):
    from django.db.models import F
    from django.utils import timezone

    from .models import ErrorRegistrado

    if not registro.exc_info or not registro.exc_info[0]:
        return
    tipo_exc, valor, rastro = registro.exc_info
    request = getattr(registro, "request", None)
    ruta = getattr(request, "path", "")[:300]
    # La ruta con su patrón (/catalogo/producto/<int:pk>/) junta los errores de todos los productos.
    coincidencia = getattr(request, "resolver_match", None)
    patron = getattr(coincidencia, "route", "") or ruta
    ultimo_marco = traceback.extract_tb(rastro)[-1] if rastro else None
    marco = f"{ultimo_marco.filename}:{ultimo_marco.lineno}" if ultimo_marco else ""
    tipo = f"{tipo_exc.__module__}.{tipo_exc.__qualname__}".removeprefix("builtins.")[:120]
    usuario = getattr(request, "user", None)
    datos = {
        "tipo": tipo,
        "mensaje": str(valor)[:500],
        "ruta": ruta,
        "metodo": getattr(request, "method", "")[:10],
        "usuario": usuario.get_username()[:150] if getattr(usuario, "is_authenticated", False) else "",
        "detalle": "".join(traceback.format_exception(tipo_exc, valor, rastro))[-20000:],
        "ultima": timezone.now(),
        "revisado": False,
    }
    firma = _firma(tipo, marco, patron)
    if not ErrorRegistrado.objects.filter(firma=firma).update(veces=F("veces") + 1, **datos):
        ErrorRegistrado.objects.create(firma=firma, **datos)
        sobrantes = ErrorRegistrado.objects.order_by("-ultima").values_list("pk", flat=True)[MAXIMO_GUARDADOS:]
        ErrorRegistrado.objects.filter(pk__in=list(sobrantes)).delete()


class GuardarError(logging.Handler):
    def emit(self, record):
        try:
            guardar(record)
        except Exception:  # p. ej. la base de datos no responde: no se puede guardar, se sigue
            pass
