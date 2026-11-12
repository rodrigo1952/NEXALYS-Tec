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
        RESPONDER_SOLICITUD = "responder_derecho", "Respondió una solicitud de datos personales"

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


class ErrorRegistrado(models.Model):
    """
    Error de la página (respuesta 500) para que el administrador se entere sin mirar el servidor.

    Los errores iguales (mismo tipo, mismo lugar del código y misma página) se juntan en una sola fila
    que cuenta cuántas veces pasó. Lo guarda administracion/registro_errores.py.
    No guarda contraseñas ni lo que la persona escribió en los formularios: solo dónde falló el código.
    """

    firma = models.CharField("firma", max_length=64, unique=True)
    tipo = models.CharField("tipo de error", max_length=120)
    mensaje = models.CharField("mensaje", max_length=500, blank=True)
    ruta = models.CharField("página", max_length=300)
    metodo = models.CharField("método", max_length=10, blank=True)
    usuario = models.CharField("cuenta", max_length=150, blank=True)
    detalle = models.TextField("detalle técnico", blank=True)
    veces = models.PositiveIntegerField("veces", default=1)
    primera = models.DateTimeField("primera vez", auto_now_add=True)
    ultima = models.DateTimeField("última vez", db_index=True)
    revisado = models.BooleanField("revisado", default=False)

    class Meta:
        ordering = ["revisado", "-ultima"]
        verbose_name = "error de la página"
        verbose_name_plural = "errores de la página"

    def __str__(self):
        return f"{self.tipo} en {self.ruta} ({self.veces})"
