from urllib.parse import quote

from django.conf import settings
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models, transaction
from django.utils import timezone

from catalogo.imagenes import LADO_MAXIMO_LOGO, optimizar_campo
from catalogo.models import EXTENSIONES_IMAGEN, validar_tamano_imagen

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
    logo = models.ImageField(
        "logo",
        upload_to="tiendas/logos/",
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=EXTENSIONES_IMAGEN),
            validar_tamano_imagen,
        ],
        help_text="Opcional. JPG, PNG o WEBP de máximo 2 MB. Se recomienda una imagen cuadrada.",
    )
    estado = models.CharField(
        "estado",
        max_length=12,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    motivo_suspension = models.TextField(
        "motivo de la suspensión",
        blank=True,
        help_text="La tienda lo ve en su panel para saber qué corregir.",
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

    def suspender(self, motivo):
        """El administrador suspende la tienda: sus productos se ocultan del catálogo."""
        self.estado = self.Estado.SUSPENDIDA
        self.motivo_suspension = motivo.strip()
        self.save(update_fields=["estado", "motivo_suspension"])

    def reactivar(self):
        """
        Regla: vuelve a ACTIVA solo si ya verificó su correo; si no, queda PENDIENTE
        hasta que lo verifique. El motivo de la suspensión se borra.
        """
        self.estado = self.Estado.ACTIVA if self.verificada_en else self.Estado.PENDIENTE
        self.motivo_suspension = ""
        self.save(update_fields=["estado", "motivo_suspension"])

    def enlace_whatsapp(self, mensaje=""):
        """Enlace wa.me con el código de Perú (+51) y un mensaje predeterminado."""
        enlace = f"https://wa.me/51{self.whatsapp}"
        if mensaje:
            enlace += f"?text={quote(mensaje)}"
        return enlace

    def enlace_mapa(self):
        """Enlace de búsqueda de la dirección en Google Maps."""
        return "https://www.google.com/maps/search/?api=1&query=" + quote(self.direccion)

    def save(self, *args, **kwargs):
        if kwargs.get("update_fields") is None:
            optimizar_campo(self.logo, LADO_MAXIMO_LOGO)
        # Al cambiar o quitar el logo, se borra el archivo anterior.
        anterior = None
        if self.pk:
            anterior = Tienda.objects.filter(pk=self.pk).values_list("logo", flat=True).first()
        super().save(*args, **kwargs)
        if anterior and anterior != (self.logo.name or ""):
            almacenamiento = self.logo.storage
            transaction.on_commit(lambda: almacenamiento.delete(anterior))

    # --- Horario de atención ------------------------------------------------------
    def horario_semana(self):
        """Lista de (día, texto) de lunes a domingo, p. ej. ("Lunes", "9:00 a. m. – 6:00 p. m.")."""
        por_dia = {h.dia: h for h in self.horarios.all()}
        semana = []
        for dia, nombre in HorarioDia.Dia.choices:
            horario = por_dia.get(dia)
            semana.append((nombre, horario.texto if horario else "Cerrado"))
        return semana

    def tiene_horario(self):
        return any(h.abre is not None for h in self.horarios.all())

    def estado_atencion(self, ahora=None):
        """
        Indica si la tienda está abierta según la hora de Perú (TIME_ZONE = America/Lima),
        teniendo en cuenta el refrigerio. Devuelve None si la tienda no registró su horario.
        """
        por_dia = {h.dia: h for h in self.horarios.all() if h.abre is not None}
        if not por_dia:
            return None
        ahora = timezone.localtime(ahora)
        hoy, hora = ahora.weekday(), ahora.time()

        horario_hoy = por_dia.get(hoy)
        if horario_hoy:
            for inicio, fin in horario_hoy.tramos():
                if inicio <= hora < fin:
                    if horario_hoy.tiene_refrigerio and fin == horario_hoy.descanso_inicio:
                        motivo = "cierra por refrigerio"
                    else:
                        motivo = "cierra"
                    return {"abierto": True, "texto": f"Abierto ahora · {motivo} {a_las(fin)}"}
                if hora < inicio:
                    if horario_hoy.tiene_refrigerio and inicio == horario_hoy.descanso_fin:
                        return {"abierto": False, "texto": f"Cerrado por refrigerio · vuelve a abrir {a_las(inicio)}"}
                    return {"abierto": False, "texto": f"Cerrado ahora · abre hoy {a_las(inicio)}"}
        for dias_despues in range(1, 8):
            dia = (hoy + dias_despues) % 7
            if dia in por_dia:
                cuando = "mañana" if dias_despues == 1 else f"el {HorarioDia.Dia(dia).label.lower()}"
                return {"abierto": False, "texto": f"Cerrado ahora · abre {cuando} {a_las(por_dia[dia].abre)}"}
        return None


def hora_12(hora):
    """time(13, 30) -> '1:30 p. m.'  (formato de 12 horas que se usa en Perú)"""
    sufijo = "a. m." if hora.hour < 12 else "p. m."
    return f"{hora.hour % 12 or 12}:{hora.minute:02d} {sufijo}"


def a_las(hora):
    """'a la 1:00 p. m.' o 'a las 3:00 p. m.' (en español se dice 'a la una')."""
    articulo = "a la" if hora.hour % 12 == 1 else "a las"
    return f"{articulo} {hora_12(hora)}"


class HorarioDia(models.Model):
    """
    Horario de atención de una tienda para un día de la semana.
    Sin horas = ese día cierra. El refrigerio (descanso al mediodía) es opcional.
    """

    class Dia(models.IntegerChoices):
        LUNES = 0, "Lunes"
        MARTES = 1, "Martes"
        MIERCOLES = 2, "Miércoles"
        JUEVES = 3, "Jueves"
        VIERNES = 4, "Viernes"
        SABADO = 5, "Sábado"
        DOMINGO = 6, "Domingo"

    tienda = models.ForeignKey(Tienda, on_delete=models.CASCADE, related_name="horarios", verbose_name="tienda")
    dia = models.PositiveSmallIntegerField("día", choices=Dia.choices)
    abre = models.TimeField("abre", null=True, blank=True)
    cierra = models.TimeField("cierra", null=True, blank=True)
    descanso_inicio = models.TimeField("inicio del refrigerio", null=True, blank=True)
    descanso_fin = models.TimeField("fin del refrigerio", null=True, blank=True)

    class Meta:
        ordering = ["dia"]
        verbose_name = "horario"
        verbose_name_plural = "horarios"
        constraints = [
            models.UniqueConstraint(fields=["tienda", "dia"], name="horario_unico_por_dia"),
        ]

    def __str__(self):
        return f"{self.get_dia_display()}: {self.texto}"

    @property
    def tiene_refrigerio(self):
        return self.descanso_inicio is not None and self.descanso_fin is not None

    def tramos(self):
        """Periodos en que la tienda atiende ese día, p. ej. [(8:00, 13:00), (15:00, 22:00)]."""
        if self.abre is None or self.cierra is None:
            return []
        if self.tiene_refrigerio:
            return [(self.abre, self.descanso_inicio), (self.descanso_fin, self.cierra)]
        return [(self.abre, self.cierra)]

    @property
    def texto(self):
        tramos = self.tramos()
        if not tramos:
            return "Cerrado"
        return " y ".join(f"{hora_12(inicio)} – {hora_12(fin)}" for inicio, fin in tramos)
