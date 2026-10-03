from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models

PRECIO_MINIMO = Decimal("0.10")
TAMANO_MAXIMO_IMAGEN_MB = 2
EXTENSIONES_IMAGEN = ["jpg", "jpeg", "png", "webp"]


def validar_tamano_imagen(archivo):
    """Validación: la imagen del producto no puede pesar más de 2 MB."""
    if archivo and archivo.size > TAMANO_MAXIMO_IMAGEN_MB * 1024 * 1024:
        raise ValidationError(f"La imagen no debe superar los {TAMANO_MAXIMO_IMAGEN_MB} MB.")


class Categoria(models.Model):
    """CU-07: las categorías las gestiona el administrador."""

    nombre = models.CharField("nombre", max_length=60, unique=True)
    activa = models.BooleanField("activa", default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "categoría"
        verbose_name_plural = "categorías"

    def __str__(self):
        return self.nombre


class Marca(models.Model):
    """CU-07: las marcas las gestiona el administrador."""

    nombre = models.CharField("nombre", max_length=60, unique=True)
    activa = models.BooleanField("activa", default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "marca"
        verbose_name_plural = "marcas"

    def __str__(self):
        return self.nombre


class ProductoQuerySet(models.QuerySet):
    def visibles(self):
        """
        Regla de negocio: el catálogo público solo muestra productos publicados
        de tiendas ACTIVAS (verificadas y no suspendidas).
        """
        return self.filter(activo=True, tienda__estado="activa")


class Producto(models.Model):
    """CU-03 Gestionar productos."""

    tienda = models.ForeignKey(
        "tiendas.Tienda",
        on_delete=models.CASCADE,
        related_name="productos",
        verbose_name="tienda",
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="productos",
        verbose_name="categoría",
    )
    marca = models.ForeignKey(
        Marca,
        on_delete=models.PROTECT,
        related_name="productos",
        verbose_name="marca",
    )
    nombre = models.CharField("nombre", max_length=150)
    descripcion = models.TextField("descripción", blank=True)
    precio = models.DecimalField(
        "precio (S/)",
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(PRECIO_MINIMO, message="El precio debe ser de al menos S/ 0.10.")],
    )
    stock = models.PositiveIntegerField("stock", default=0)
    imagen = models.ImageField(
        "imagen",
        upload_to="productos/",
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=EXTENSIONES_IMAGEN),
            validar_tamano_imagen,
        ],
        help_text="Opcional. JPG, PNG o WEBP de máximo 2 MB.",
    )
    activo = models.BooleanField(
        "publicado",
        default=True,
        help_text="Desmárcalo para ocultar el producto del catálogo sin eliminarlo.",
    )
    creado = models.DateTimeField("creado", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    objects = ProductoQuerySet.as_manager()

    class Meta:
        ordering = ["-creado"]
        verbose_name = "producto"
        verbose_name_plural = "productos"
        constraints = [
            models.UniqueConstraint(fields=["tienda", "nombre"], name="producto_unico_por_tienda"),
        ]

    def __str__(self):
        return self.nombre

    @property
    def agotado(self):
        return self.stock == 0

    def mensaje_whatsapp(self):
        return f"Hola, me interesa el producto \"{self.nombre}\" (S/ {self.precio}) que vi en NEXALYS Tec."

    def enlace_whatsapp(self):
        return self.tienda.enlace_whatsapp(self.mensaje_whatsapp())
