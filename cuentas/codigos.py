"""
Códigos de 6 dígitos para confirmar el correo (clientes) y verificar la tienda.

- nuevo(usuario) → "482913": crea el código y guarda solo su huella (HMAC con la SECRET_KEY).
  Un código nuevo reemplaza al anterior.
- es_valido(usuario, "482 913", horas) → True si coincide y no venció. Acepta espacios o guiones.
- borrar(usuario): al confirmar, el código ya no sirve.

Contra quien prueba códigos al azar: límite de intentos (cuentas/limites.py, CODIGO): 5 cada 15 minutos.
"""

import hashlib
import hmac
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import CodigoVerificacion


def _huella(usuario_id, codigo):
    return hmac.new(settings.SECRET_KEY.encode(), f"codigo:{usuario_id}:{codigo}".encode(), hashlib.sha256).hexdigest()


def nuevo(usuario):
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    CodigoVerificacion.objects.update_or_create(
        usuario=usuario, defaults={"huella": _huella(usuario.pk, codigo), "creado": timezone.now()}
    )
    return codigo


def limpiar(texto):
    return re.sub(r"\D", "", texto or "")


def es_valido(usuario, texto, horas):
    codigo = limpiar(texto)
    if usuario is None or len(codigo) != 6:
        return False
    guardado = CodigoVerificacion.objects.filter(usuario=usuario).first()
    if guardado is None or guardado.creado < timezone.now() - timedelta(hours=horas):
        return False
    return hmac.compare_digest(guardado.huella, _huella(usuario.pk, codigo))


def borrar(usuario):
    CodigoVerificacion.objects.filter(usuario=usuario).delete()
