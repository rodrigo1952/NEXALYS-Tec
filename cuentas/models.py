from django.conf import settings
from django.db import models

# Regla de negocio: una cuenta de cliente que no confirma su correo en este plazo se elimina sola.
DIAS_PARA_CONFIRMAR_CORREO = 7


class CorreoPendiente(models.Model):
    """
    Cuenta de cliente que todavía no confirmó su correo.

    Mientras exista este registro, la cuenta está inactiva (no puede iniciar sesión).
    Al abrir el enlace del correo, la cuenta se activa y el registro se borra.
    Los clientes registrados antes de esta regla no tienen registro: ya cuentan como confirmados.
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="correo_pendiente", verbose_name="usuario"
    )
    creado = models.DateTimeField("registrado el", auto_now_add=True)

    class Meta:
        verbose_name = "correo sin confirmar"
        verbose_name_plural = "correos sin confirmar"

    def __str__(self):
        return f"{self.usuario} (sin confirmar)"
