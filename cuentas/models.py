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


class ConsentimientoPrivacidad(models.Model):
    """
    Prueba de que la persona aceptó la política de privacidad (Ley 29733): qué versión, cuándo,
    desde qué conexión y en qué formulario. Si la política cambia (cuentas/privacidad.py,
    VERSION_POLITICA), se le pide aceptar de nuevo y queda otro registro.
    """

    class Origen(models.TextChoices):
        REGISTRO_CLIENTE = "registro_cliente", "Al registrarse como cliente"
        REGISTRO_TIENDA = "registro_tienda", "Al registrar su tienda"
        AL_ENTRAR = "al_entrar", "Al iniciar sesión (política nueva o cuenta anterior)"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="consentimientos", verbose_name="usuario"
    )
    version = models.CharField("versión de la política", max_length=20)
    origen = models.CharField("dónde aceptó", max_length=20, choices=Origen.choices)
    ip = models.CharField("conexión (IP)", max_length=45, blank=True)
    fecha = models.DateTimeField("fecha")

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "consentimiento de privacidad"
        verbose_name_plural = "consentimientos de privacidad"
        indexes = [models.Index(fields=["usuario", "version"], name="consentimiento_usuario_version")]

    def __str__(self):
        return f"{self.usuario} aceptó la versión {self.version}"


class SolicitudDerecho(models.Model):
    """
    Pedido de una persona sobre sus datos personales (derechos de la Ley 29733): información,
    acceso, rectificación, cancelación u oposición. Llega a la consola del administrador con la
    fecha límite para responder (días hábiles, ver cuentas/privacidad.py).
    """

    class Tipo(models.TextChoices):
        INFORMACION = "informacion", "Información: saber qué datos tratamos y para qué"
        ACCESO = "acceso", "Acceso: recibir una copia de mis datos"
        RECTIFICACION = "rectificacion", "Rectificación: corregir un dato"
        CANCELACION = "cancelacion", "Cancelación: borrar mis datos"
        OPOSICION = "oposicion", "Oposición: que dejen de usar mis datos para algo"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ATENDIDA = "atendida", "Respondida"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="solicitudes_derechos", verbose_name="cuenta",
    )
    nombre = models.CharField("nombre completo", max_length=150)
    correo = models.EmailField("correo para responderte")
    tipo = models.CharField("qué pides", max_length=20, choices=Tipo.choices)
    detalle = models.TextField("detalle", max_length=2000)
    creada = models.DateTimeField("recibida el", auto_now_add=True)
    vence = models.DateField("responder hasta")
    estado = models.CharField("estado", max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    respuesta = models.TextField("respuesta", blank=True)
    atendida_en = models.DateTimeField("respondida el", null=True, blank=True)
    atendida_por = models.CharField("respondida por", max_length=150, blank=True)

    class Meta:
        ordering = ["estado", "vence", "creada"]
        verbose_name = "solicitud de derechos (datos personales)"
        verbose_name_plural = "solicitudes de derechos (datos personales)"

    def __str__(self):
        return f"{self.get_tipo_display().split(':')[0]} · {self.nombre} · {self.creada:%d/%m/%Y}"

    @property
    def nombre_corto_tipo(self):
        return self.get_tipo_display().split(":")[0]

    @property
    def dias_restantes(self):
        from django.utils import timezone

        return (self.vence - timezone.localdate()).days
