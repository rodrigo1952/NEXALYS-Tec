"""
Limpieza automática de cuentas.

1. Tiendas suspendidas que no se reactivaron en 90 días: se eliminan (cuenta, tienda,
   productos e imágenes). Sus ventas se CONSERVAN ANÓNIMAS como "Tienda eliminada",
   sin los datos del cliente, para que las estadísticas no cambien. Sus ingresos,
   proveedores y kardex (datos privados de la tienda) se eliminan con ella.
   Queda registrado en el Historial del administrador.
2. Cuentas de cliente que no confirmaron su correo en 7 días: se eliminan, para que
   un correo mal escrito no deje el nombre de usuario ocupado para siempre.

Django no tiene un reloj que trabaje solo, así que la limpieza se ejecuta:
  - cada vez que un administrador entra al Resumen o a Tiendas del panel, y
  - con el comando  python manage.py limpiar_cuentas  (para programarlo en el
    servidor cuando la página se publique).
"""

from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from catalogo.archivos import carpeta_tienda
from catalogo.models import borrar_archivo_al_confirmar
from catalogo.reubicar import borrar_carpetas_vacias
from cuentas.models import DIAS_PARA_CONFIRMAR_CORREO
from inventario.models import Venta
from tiendas.models import DIAS_PARA_ELIMINAR_SUSPENDIDA, Tienda

from . import acciones
from .models import AccionAdmin

NOMBRE_ANONIMO = "Tienda eliminada"


def tiendas_vencidas(ahora=None):
    limite = (ahora or timezone.now()) - timedelta(days=DIAS_PARA_ELIMINAR_SUSPENDIDA)
    return Tienda.objects.filter(estado=Tienda.Estado.SUSPENDIDA, suspendida_en__lte=limite)


def eliminar_tienda_vencida(tienda):
    """Elimina una tienda suspendida hace más de 90 días, conservando sus ventas anónimas."""
    with transaction.atomic():
        tienda = Tienda.objects.select_for_update().select_related("usuario").get(pk=tienda.pk)
        if tienda.estado != Tienda.Estado.SUSPENDIDA:
            return False  # alguien la reactivó justo ahora
        nombre, carpeta = tienda.nombre, carpeta_tienda(tienda)
        suspendida = timezone.localtime(tienda.suspendida_en).strftime("%d/%m/%Y")
        motivo = tienda.motivo_suspension or "sin motivo registrado"

        # Ventas anónimas: se quitan la tienda y los datos personales del cliente.
        Venta.objects.filter(tienda=tienda).update(
            tienda=None, tienda_nombre=NOMBRE_ANONIMO, usuario=None,
            cliente_nombre="Cliente anónimo", cliente_documento="", nota="", motivo_anulacion="",
        )
        tienda.movimientos.all().delete()  # el kardex es privado de la tienda
        for producto in tienda.productos.all():
            producto.delete()  # también borra sus imágenes
        borrar_archivo_al_confirmar(tienda.logo)
        tienda.usuario.delete()  # borra la cuenta, la tienda y su horario
        acciones.registrar(
            None, AccionAdmin.Tipo.ELIMINACION_AUTOMATICA, f"Tienda «{nombre}»",
            f"Suspendida desde el {suspendida} y no se reactivó en {DIAS_PARA_ELIMINAR_SUSPENDIDA} días. "
            f"Motivo de la suspensión: {motivo}",
        )
    transaction.on_commit(lambda: borrar_carpetas_vacias(carpeta))
    return True


def cuentas_sin_confirmar_vencidas(ahora=None):
    limite = (ahora or timezone.now()) - timedelta(days=DIAS_PARA_CONFIRMAR_CORREO)
    return User.objects.filter(is_active=False, correo_pendiente__creado__lte=limite)


def ejecutar(ahora=None):
    """Hace toda la limpieza pendiente. Devuelve (tiendas eliminadas, cuentas eliminadas)."""
    tiendas = sum(1 for tienda in tiendas_vencidas(ahora) if eliminar_tienda_vencida(tienda))
    cuentas = list(cuentas_sin_confirmar_vencidas(ahora).values_list("pk", flat=True))
    if cuentas:
        User.objects.filter(pk__in=cuentas).delete()
    return tiendas, len(cuentas)


def por_eliminarse_pronto():
    """Tiendas suspendidas, de la que se eliminará antes a la que se eliminará después."""
    return Tienda.objects.filter(estado=Tienda.Estado.SUSPENDIDA, suspendida_en__isnull=False).order_by("suspendida_en")
