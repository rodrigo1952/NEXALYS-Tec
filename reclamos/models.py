"""
Libro de Reclamaciones virtual (Código de Protección y Defensa del Consumidor; Reglamento del Libro
de Reclamaciones, D.S. 011-2011-PCM; Ley 32495 para el comercio electrónico).

Cada hoja va dirigida a un proveedor: NEXALYS Tec (la plataforma) o una tienda. La tienda responde
las suyas desde su panel y el administrador las supervisa; las de NEXALYS las responde el administrador.
Plazo para responder: 15 días hábiles. Las hojas no se borran: se conservan al menos 2 años.
"""

from django.conf import settings
from django.db import models, transaction
from django.db.models import Max
from django.utils import timezone

PLAZO_DIAS_HABILES = 15


class Reclamo(models.Model):
    class Tipo(models.TextChoices):
        RECLAMO = "reclamo", "Reclamo"
        QUEJA = "queja", "Queja"

    class Bien(models.TextChoices):
        PRODUCTO = "producto", "Producto"
        SERVICIO = "servicio", "Servicio"

    class Documento(models.TextChoices):
        DNI = "dni", "DNI"
        CE = "ce", "Carné de extranjería"
        PASAPORTE = "pasaporte", "Pasaporte"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        RESPONDIDO = "respondido", "Respondido"

    # --- Hoja y proveedor (se copian sus datos: la hoja no cambia aunque la tienda cambie o se elimine) ---
    proveedor_clave = models.CharField("proveedor (clave)", max_length=30, editable=False)  # «nexalys» o «tienda-5»
    anio = models.PositiveSmallIntegerField("año", editable=False)
    numero = models.PositiveIntegerField("número correlativo", editable=False)
    tienda = models.ForeignKey(
        "tiendas.Tienda", on_delete=models.SET_NULL, null=True, blank=True, related_name="reclamos",
        verbose_name="tienda reclamada",
    )
    proveedor_nombre = models.CharField("proveedor", max_length=150)
    proveedor_ruc = models.CharField("RUC del proveedor", max_length=20, blank=True)
    proveedor_direccion = models.CharField("dirección del proveedor", max_length=250, blank=True)
    creado = models.DateTimeField("presentado el", default=timezone.now)
    ip = models.CharField("conexión (IP)", max_length=45, blank=True)

    # --- 1. Consumidor ---
    nombre = models.CharField("nombres y apellidos", max_length=150)
    documento_tipo = models.CharField("tipo de documento", max_length=10, choices=Documento.choices, default=Documento.DNI)
    documento_numero = models.CharField("número de documento", max_length=20)
    domicilio = models.CharField("domicilio", max_length=250)
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    correo = models.EmailField("correo electrónico")
    menor_de_edad = models.BooleanField("soy menor de edad", default=False)
    apoderado = models.CharField(
        "nombre del padre, madre o apoderado", max_length=150, blank=True,
        help_text="Solo si eres menor de edad.",
    )

    # --- 2. Bien contratado ---
    bien = models.CharField("tipo de bien", max_length=10, choices=Bien.choices, default=Bien.PRODUCTO)
    descripcion_bien = models.CharField("producto o servicio", max_length=250, help_text="Marca, modelo o el servicio que recibiste.")
    monto = models.DecimalField("monto reclamado (S/)", max_digits=10, decimal_places=2, null=True, blank=True)
    comprobante = models.CharField("boleta, factura o nota de venta", max_length=40, blank=True, help_text="Déjalo vacío si no tienes comprobante.")
    fecha_compra = models.DateField("fecha de la compra o del servicio", null=True, blank=True)

    # --- 3. Detalle ---
    tipo = models.CharField("tipo", max_length=10, choices=Tipo.choices, default=Tipo.RECLAMO)
    detalle = models.TextField("detalle", max_length=3000)
    pedido = models.TextField("pedido", max_length=1500)

    # --- 4. Respuesta del proveedor (observaciones y acciones adoptadas) ---
    vence = models.DateField("responder hasta")
    estado = models.CharField("estado", max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    respuesta = models.TextField("observaciones y acciones del proveedor", blank=True)
    respondido_en = models.DateTimeField("respondido el", null=True, blank=True)
    respondido_por = models.CharField("respondido por", max_length=150, blank=True)

    class Meta:
        ordering = ["-creado"]
        verbose_name = "hoja de reclamación"
        verbose_name_plural = "libro de reclamaciones"
        constraints = [
            models.UniqueConstraint(fields=["proveedor_clave", "anio", "numero"], name="reclamo_correlativo_unico"),
        ]

    def __str__(self):
        return f"Hoja {self.codigo} · {self.proveedor_nombre}"

    @property
    def codigo(self):
        """Número de la hoja: 000001-2026 (correlativo por proveedor y año)."""
        return f"{self.numero:06d}-{self.anio}"

    @property
    def dias_restantes(self):
        return (self.vence - timezone.localdate()).days

    @classmethod
    def clave_de(cls, tienda):
        return f"tienda-{tienda.pk}" if tienda else "nexalys"

    def save(self, *args, **kwargs):
        if not self.pk and not self.numero:
            # El correlativo se calcula dentro de la transacción (SQLite IMMEDIATE: una hoja a la vez).
            with transaction.atomic():
                self.proveedor_clave = self.clave_de(self.tienda)
                self.anio = timezone.localdate(self.creado).year
                ultimo = (
                    Reclamo.objects.filter(proveedor_clave=self.proveedor_clave, anio=self.anio)
                    .aggregate(m=Max("numero"))["m"] or 0
                )
                self.numero = ultimo + 1
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)


def datos_nexalys():
    """Datos de la plataforma como proveedor (los mismos del responsable de privacidad, en el .env)."""
    return {
        "nombre": settings.PRIVACIDAD_TITULAR or "NEXALYS Tec",
        "ruc": settings.PRIVACIDAD_DOCUMENTO,
        "direccion": settings.PRIVACIDAD_DIRECCION,
    }
