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


class ClaveTemporal(models.Model):
    """
    Clave temporal que el administrador generó para alguien que no podía entrar.

    - Vence a las 24 horas (HORAS_CLAVE_TEMPORAL): después ya no sirve para entrar.
    - Al entrar con ella, la persona está obligada a crear su propia contraseña.
    - «huella» es la contraseña cifrada en ese momento: si la persona la cambia por otro
      camino (p. ej. «¿Olvidaste tu contraseña?»), la huella ya no coincide y el registro se ignora.
    La clave en sí NUNCA se guarda: solo se muestra una vez al administrador.
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="clave_temporal", verbose_name="usuario"
    )
    creada = models.DateTimeField("generada el")
    vence = models.DateTimeField("vence el")
    huella = models.CharField("contraseña cifrada al generarla", max_length=128)

    class Meta:
        verbose_name = "clave temporal"
        verbose_name_plural = "claves temporales"

    def __str__(self):
        return f"Clave temporal de {self.usuario}"

    def sigue_puesta(self):
        """True si la contraseña de la cuenta todavía es la clave temporal."""
        return self.usuario.password == self.huella

    def vencida(self, ahora=None):
        from django.utils import timezone

        return (ahora or timezone.now()) >= self.vence


class IntentoAcceso(models.Model):
    """
    Registro para el límite de intentos (cuentas/limites.py): cada contraseña equivocada al iniciar
    sesión y cada correo pedido (reenviar enlace o recuperar contraseña). Se borran solos al día siguiente.
    No guarda contraseñas: solo qué se intentó, para quién (usuario o correo) y desde qué conexión (IP).
    """

    accion = models.CharField("acción", max_length=20)
    clave = models.CharField("usuario o correo", max_length=254, blank=True)
    ip = models.CharField("conexión (IP)", max_length=45, blank=True)
    creado = models.DateTimeField("fecha", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "intento de acceso"
        verbose_name_plural = "intentos de acceso"
        indexes = [models.Index(fields=["accion", "creado"], name="intento_accion_fecha")]

    def __str__(self):
        return f"{self.accion} · {self.clave or '-'} · {self.ip or '-'}"
