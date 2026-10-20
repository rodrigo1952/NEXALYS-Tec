"""
Acciones del administrador sobre tiendas y cuentas.

Cada acción:
  - bloquea la fila mientras trabaja (select_for_update), así dos administradores
    que hacen clic a la vez no dejan la cuenta o la tienda en un estado mezclado;
  - queda registrada en el historial (AccionAdmin) con su motivo.

Reglas de negocio:
  - Desactivar la cuenta de una tienda también SUSPENDE su tienda (con el mismo motivo):
    una cuenta desactivada no debe seguir mostrando productos.
  - Reactivar la cuenta de una tienda también reactiva su tienda.
  - Reactivar una tienda también reactiva la cuenta de su dueño si estaba desactivada.
"""

from django.contrib.auth.models import User
from django.db import transaction

from tiendas.models import Tienda

from .models import AccionAdmin

Tipo = AccionAdmin.Tipo


def registrar(admin, tipo, objetivo, motivo="", usuario=None):
    return AccionAdmin.objects.create(
        admin=admin,
        admin_nombre=admin.get_username() if admin else "",
        tipo=tipo,
        objetivo=objetivo[:250],
        usuario_afectado=usuario,
        motivo=(motivo or "").strip(),
    )


def texto_tienda(tienda):
    return f"Tienda «{tienda.nombre}»"


def texto_cuenta(usuario):
    return f"Cuenta «{usuario.get_username()}»"


def suspender_tienda(admin, tienda, motivo):
    """Devuelve False si la tienda ya estaba suspendida (otro administrador se adelantó)."""
    with transaction.atomic():
        tienda = Tienda.objects.select_for_update().get(pk=tienda.pk)
        if tienda.estado == Tienda.Estado.SUSPENDIDA:
            return False
        tienda.suspender(motivo)
        registrar(admin, Tipo.SUSPENDER_TIENDA, texto_tienda(tienda), motivo, tienda.usuario)
    return True


def reactivar_tienda(admin, tienda, motivo=""):
    """Devuelve la tienda actualizada, o None si ya no estaba suspendida."""
    with transaction.atomic():
        tienda = Tienda.objects.select_for_update().select_related("usuario").get(pk=tienda.pk)
        if tienda.estado != Tienda.Estado.SUSPENDIDA:
            return None
        tienda.reactivar()
        dueno = User.objects.select_for_update().get(pk=tienda.usuario_id)
        if not dueno.is_active:
            dueno.is_active = True
            dueno.save(update_fields=["is_active"])
        registrar(admin, Tipo.REACTIVAR_TIENDA, texto_tienda(tienda), motivo, dueno)
    return tienda


def desactivar_cuenta(admin, usuario, motivo):
    """Devuelve False si la cuenta ya estaba desactivada."""
    with transaction.atomic():
        usuario = User.objects.select_for_update().get(pk=usuario.pk)
        if not usuario.is_active:
            return False
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])
        tienda = Tienda.objects.select_for_update().filter(usuario=usuario).first()
        if tienda is not None and tienda.estado != Tienda.Estado.SUSPENDIDA:
            tienda.suspender(motivo)
        registrar(admin, Tipo.DESACTIVAR_CUENTA, texto_cuenta(usuario), motivo, usuario)
    return True


def reactivar_cuenta(admin, usuario, motivo=""):
    """Devuelve False si la cuenta ya estaba activa."""
    with transaction.atomic():
        usuario = User.objects.select_for_update().get(pk=usuario.pk)
        if usuario.is_active:
            return False
        usuario.is_active = True
        usuario.save(update_fields=["is_active"])
        tienda = Tienda.objects.select_for_update().filter(usuario=usuario).first()
        if tienda is not None and tienda.estado == Tienda.Estado.SUSPENDIDA:
            tienda.reactivar()
        registrar(admin, Tipo.REACTIVAR_CUENTA, texto_cuenta(usuario), motivo, usuario)
    return True


def motivo_desactivacion(usuario):
    """El motivo de la última desactivación de la cuenta (para mostrarlo al iniciar sesión)."""
    return (
        AccionAdmin.objects.filter(usuario_afectado=usuario, tipo=Tipo.DESACTIVAR_CUENTA)
        .values_list("motivo", flat=True)
        .first()
    )
