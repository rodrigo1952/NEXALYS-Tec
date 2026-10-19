from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import BooleanField, Case, DecimalField, F, IntegerField, Q, Value, When
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone

from .busqueda import normalizar
from .imagenes import LADO_MAXIMO_PRODUCTO, optimizar_campo

PRECIO_MINIMO = Decimal("0.10")
TAMANO_MAXIMO_IMAGEN_MB = 2
EXTENSIONES_IMAGEN = ["jpg", "jpeg", "png", "webp"]
MAX_DESTACADOS = 3
MAX_FOTOS_EXTRA = 5


def validar_tamano_imagen(archivo):
    """Validación: la imagen del producto no puede pesar más de 2 MB."""
    if archivo and archivo.size > TAMANO_MAXIMO_IMAGEN_MB * 1024 * 1024:
        raise ValidationError(f"La imagen no debe superar los {TAMANO_MAXIMO_IMAGEN_MB} MB.")


def borrar_archivo_al_confirmar(campo):
    """Borra el archivo de una imagen solo si la transacción se confirma."""
    nombre = campo.name
    if nombre:
        almacenamiento = campo.storage
        transaction.on_commit(lambda: almacenamiento.delete(nombre))


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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Producto.actualizar_texto_busqueda(self.productos.all())


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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Producto.actualizar_texto_busqueda(self.productos.all())


def q_oferta_vigente(prefijo=""):
    """
    Condición de "oferta vigente" para consultas: hay precio de oferta, es menor
    que el normal y no venció. prefijo="producto__" para usarla desde otro modelo.
    """
    hoy = timezone.localdate()
    return (
        Q(**{f"{prefijo}precio_oferta__isnull": False})
        & Q(**{f"{prefijo}precio_oferta__lt": F(f"{prefijo}precio")})
        & (Q(**{f"{prefijo}oferta_hasta__isnull": True}) | Q(**{f"{prefijo}oferta_hasta__gte": hoy}))
    )


def precio_actual_expr(prefijo=""):
    """Precio que paga el cliente hoy: el de oferta si está vigente, si no el normal."""
    return Case(
        When(q_oferta_vigente(prefijo), then=F(f"{prefijo}precio_oferta")),
        default=F(f"{prefijo}precio"),
        output_field=DecimalField(max_digits=8, decimal_places=2),
    )


class ProductoQuerySet(models.QuerySet):
    def visibles(self):
        """
        Regla de negocio: el catálogo público solo muestra productos publicados,
        no ocultados por el administrador, de tiendas ACTIVAS (verificadas y no suspendidas).
        """
        return self.filter(activo=True, oculto_por_admin=False, tienda__estado="activa")

    def en_oferta(self):
        return self.filter(q_oferta_vigente())

    def con_precio_actual(self):
        """Agrega 'precio_actual' para filtrar y ordenar por el precio real (con oferta)."""
        return self.annotate(precio_actual=precio_actual_expr())

    def buscar(self, texto):
        """Búsqueda sin tildes ni mayúsculas; con varias palabras, deben estar todas."""
        resultado = self
        for palabra in normalizar(texto).split():
            resultado = resultado.filter(texto_busqueda__contains=palabra)
        return resultado

    def con_relevancia(self, texto):
        """
        Agrega dos datos a cada producto encontrado con buscar():

        - relevancia: puntaje para ordenar "Más relevantes". Por cada palabra buscada:
            10 puntos si está en el NOMBRE, 3 si está en la MARCA o CATEGORÍA y
            1 si solo está en la descripción. Si toda la frase aparece tal cual en
            el nombre, 5 puntos extra.
          Ej.: "teclado" -> el teclado Genius (10) sale antes que la laptop que
          solo lo menciona en sus características (1).
        - coincide_descripcion: True si alguna palabra solo se encontró en la
          descripción. La tarjeta muestra "Coincide con sus características".
        """
        palabras = normalizar(texto).split()
        if not palabras:
            return self.annotate(relevancia=Value(0), coincide_descripcion=Value(False))

        relevancia = Value(0)
        solo_en_descripcion = Q()
        for palabra in palabras:
            relevancia = relevancia + Case(
                When(nombre_busqueda__contains=palabra, then=Value(10)),
                When(etiquetas_busqueda__contains=palabra, then=Value(3)),
                default=Value(1),
                output_field=IntegerField(),
            )
            solo_en_descripcion |= ~Q(nombre_busqueda__contains=palabra) & ~Q(etiquetas_busqueda__contains=palabra)
        frase = " ".join(palabras)
        if len(palabras) > 1:
            relevancia = relevancia + Case(
                When(nombre_busqueda__contains=frase, then=Value(5)),
                default=Value(0),
                output_field=IntegerField(),
            )
        return self.annotate(
            relevancia=relevancia,
            coincide_descripcion=Case(
                When(solo_en_descripcion, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )


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
    precio_oferta = models.DecimalField(
        "precio de oferta (S/)",
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(PRECIO_MINIMO, message="El precio debe ser de al menos S/ 0.10.")],
        help_text="Opcional. Debe ser menor que el precio normal.",
    )
    oferta_hasta = models.DateField(
        "oferta válida hasta",
        null=True,
        blank=True,
        help_text="Opcional. Ese día es el último de la oferta; vacío = hasta que la quites.",
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
    destacado = models.BooleanField(
        "destacado en el inicio",
        default=False,
        help_text="Aparece en la sección de destacados de la página de inicio. Máximo 3 por tienda.",
    )
    oculto_por_admin = models.BooleanField(
        "oculto por el administrador",
        default=False,
        help_text="El administrador lo ocultó del catálogo; la tienda no puede volver a publicarlo.",
    )
    motivo_ocultamiento = models.TextField("motivo del ocultamiento", blank=True)
    texto_busqueda = models.TextField("texto de búsqueda", blank=True, editable=False)
    # Partes separadas del texto de búsqueda, para ordenar por relevancia.
    nombre_busqueda = models.TextField("nombre para buscar", blank=True, editable=False)
    etiquetas_busqueda = models.TextField("marca y categoría para buscar", blank=True, editable=False)
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

    # --- Ofertas ---------------------------------------------------------------
    @property
    def en_oferta(self):
        """Regla: la oferta vale si su precio es menor que el normal y no venció."""
        return (
            self.precio_oferta is not None
            and self.precio_oferta < self.precio
            and (self.oferta_hasta is None or self.oferta_hasta >= timezone.localdate())
        )

    @property
    def precio_final(self):
        """Lo que paga el cliente hoy."""
        return self.precio_oferta if self.en_oferta else self.precio

    @property
    def porcentaje_descuento(self):
        if not self.en_oferta:
            return 0
        return round((1 - self.precio_oferta / self.precio) * 100)

    # --- WhatsApp ----------------------------------------------------------------
    def mensaje_whatsapp(self):
        return f"Hola, me interesa el producto \"{self.nombre}\" (S/ {self.precio_final}) que vi en NEXALYS Tec."

    def enlace_whatsapp(self):
        return self.tienda.enlace_whatsapp(self.mensaje_whatsapp())

    # --- Búsqueda -----------------------------------------------------------------
    def campos_busqueda(self):
        """Textos sin tildes para el buscador: todo junto, solo el nombre y marca + categoría."""
        etiquetas = []
        if self.marca_id:
            etiquetas.append(self.marca.nombre)
        if self.categoria_id:
            etiquetas.append(self.categoria.nombre)
        return {
            "texto_busqueda": normalizar(" ".join([self.nombre, self.descripcion, *etiquetas])),
            "nombre_busqueda": normalizar(self.nombre),
            "etiquetas_busqueda": normalizar(" ".join(etiquetas)),
        }

    def generar_texto_busqueda(self):
        return self.campos_busqueda()["texto_busqueda"]

    @classmethod
    def actualizar_texto_busqueda(cls, productos):
        """Recalcula los textos de búsqueda (p. ej. cuando el admin renombra una marca)."""
        for producto in productos.select_related("marca", "categoria"):
            cls.objects.filter(pk=producto.pk).update(**producto.campos_busqueda())

    # --- Guardar y eliminar ---------------------------------------------------------
    def save(self, *args, **kwargs):
        # Los guardados parciales (p. ej. solo el stock al registrar un pedido) no cambian el texto.
        if kwargs.get("update_fields") is None:
            for campo, valor in self.campos_busqueda().items():
                setattr(self, campo, valor)
            optimizar_campo(self.imagen, LADO_MAXIMO_PRODUCTO)
        # Regla: al cambiar o quitar la imagen, se borra el archivo anterior
        # para no acumular imágenes que ya nadie usa.
        anterior = None
        if self.pk:
            anterior = Producto.objects.filter(pk=self.pk).values_list("imagen", flat=True).first()
        super().save(*args, **kwargs)
        if anterior and anterior != (self.imagen.name or ""):
            almacenamiento = self.imagen.storage
            transaction.on_commit(lambda: almacenamiento.delete(anterior))

    def delete(self, *args, **kwargs):
        # Al eliminar el producto, también se borra su imagen
        # (las fotos adicionales se borran con la señal de FotoProducto).
        nombre = self.imagen.name
        resultado = super().delete(*args, **kwargs)
        if nombre:
            almacenamiento = self.imagen.storage
            transaction.on_commit(lambda: almacenamiento.delete(nombre))
        return resultado


class FotoProducto(models.Model):
    """Fotos adicionales de un producto (la foto principal es Producto.imagen)."""

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="fotos",
        verbose_name="producto",
    )
    imagen = models.ImageField(
        "imagen",
        upload_to="productos/fotos/",
        validators=[
            FileExtensionValidator(allowed_extensions=EXTENSIONES_IMAGEN),
            validar_tamano_imagen,
        ],
    )
    orden = models.PositiveSmallIntegerField("orden", default=0)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "foto del producto"
        verbose_name_plural = "fotos del producto"

    def __str__(self):
        return f"Foto {self.orden + 1} de {self.producto}"

    def save(self, *args, **kwargs):
        optimizar_campo(self.imagen, LADO_MAXIMO_PRODUCTO)
        super().save(*args, **kwargs)


@receiver(post_delete, sender=FotoProducto)
def borrar_archivo_de_foto(sender, instance, **kwargs):
    # La señal también se ejecuta cuando se elimina el producto completo (CASCADE).
    borrar_archivo_al_confirmar(instance.imagen)
