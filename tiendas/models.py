from urllib.parse import quote

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

# Regla de negocio: el WhatsApp debe ser un celular peruano (9 digitos, empieza con 9).
validar_whatsapp = RegexValidator(
    regex=r"^9\d{8}$",
    message="Ingresa un número de celular peruano de 9 dígitos que empiece con 9.",
)


class Tienda(models.Model):
    """Tienda tecnológica registrada en la plataforma (actor 'Tienda' de los casos de uso)."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de verificación"
        ACTIVA = "activa", "Activa"
        SUSPENDIDA = "suspendida", "Suspendida"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tienda",
        verbose_name="usuario",
    )
    nombre = models.CharField("nombre de la tienda", max_length=100, unique=True)
    direccion = models.CharField("dirección", max_length=200)
    whatsapp = models.CharField(
        "WhatsApp",
        max_length=9,
        unique=True,
        validators=[validar_whatsapp],
        help_text="9 dígitos, sin +51 ni espacios. Ejemplo: 987654321",
    )
    descripcion = models.TextField("descripción", blank=True)
    estado = models.CharField(
        "estado",
        max_length=12,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    verificada_en = models.DateTimeField("correo verificado el", null=True, blank=True)
    creada_en = models.DateTimeField("registrada el", auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "tienda"
        verbose_name_plural = "tiendas"

    def __str__(self):
        return self.nombre

    @property
    def esta_activa(self):
        return self.estado == self.Estado.ACTIVA

    def marcar_verificada(self):
        """
        Regla de negocio: al confirmar el correo, una tienda PENDIENTE pasa a ACTIVA
        sin intervención del administrador. Una tienda SUSPENDIDA no se reactiva
        por verificar su correo: solo el administrador puede reactivarla.
        Devuelve True si la tienda cambió a ACTIVA.
        """
        if self.estado != self.Estado.PENDIENTE:
            return False
        self.estado = self.Estado.ACTIVA
        self.verificada_en = timezone.now()
        self.save(update_fields=["estado", "verificada_en"])
        return True

    def enlace_whatsapp(self, mensaje=""):
        """Enlace wa.me con el código de Perú (+51) y un mensaje predeterminado."""
        enlace = f"https://wa.me/51{self.whatsapp}"
        if mensaje:
            enlace += f"?text={quote(mensaje)}"
        return enlace

    def enlace_mapa(self):
        """Enlace de búsqueda de la dirección en Google Maps."""
        return "https://www.google.com/maps/search/?api=1&query=" + quote(self.direccion)
