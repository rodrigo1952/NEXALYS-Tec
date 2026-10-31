from django.conf import settings
from django.db import models


class AccionAdmin(models.Model):
    """
    Historial de acciones del administrador: quién hizo qué, a quién, cuándo y por qué.

    Se guarda también el texto del objetivo (p. ej. «Tienda "Tecno Q"») para que el
    registro siga siendo legible aunque la cuenta o la tienda se eliminen después.
    """

    class Tipo(models.TextChoices):
        SUSPENDER_TIENDA = "suspender_tienda", "Suspendió una tienda"
        REACTIVAR_TIENDA = "reactivar_tienda", "Reactivó una tienda"
        DESACTIVAR_CUENTA = "desactivar_cuenta", "Desactivó una cuenta"
        REACTIVAR_CUENTA = "reactivar_cuenta", "Reactivó una cuenta"
        ELIMINAR_CUENTA = "eliminar_cuenta", "Eliminó una cuenta"
        OCULTAR_PRODUCTO = "ocultar_producto", "Ocultó un producto"
        MOSTRAR_PRODUCTO = "mostrar_producto", "Volvió a mostrar un producto"
        ELIMINACION_AUTOMATICA = "eliminacion_auto", "Eliminación automática (90 días suspendida)"
        RESTABLECER_CLAVE = "restablecer_clave", "Restableció una contraseña"

    fecha = models.DateTimeField("fecha", auto_now_add=True, db_index=True)
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acciones_realizadas",
        verbose_name="administrador",
    )
    admin_nombre = models.CharField("administrador (nombre)", max_length=150)
    tipo = models.CharField("acción", max_length=20, choices=Tipo.choices)
    objetivo = models.CharField("sobre", max_length=250)
    usuario_afectado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acciones_recibidas",
        verbose_name="cuenta afectada",
    )
    motivo = models.TextField("motivo", blank=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "acción del administrador"
        verbose_name_plural = "historial del administrador"

    def __str__(self):
        return f"{self.fecha:%d/%m/%Y %H:%M} · {self.admin_nombre} · {self.get_tipo_display()} · {self.objetivo}"
