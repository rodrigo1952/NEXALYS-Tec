"""
Inventario de cada tienda (reemplazará a la sección Pedidos).

Todo es PRIVADO de cada tienda: costos, ganancias, proveedores y clientes.
El administrador solo verá totales de ventas.

- FichaInventario: datos internos de un producto (costo, stock mínimo, código).
  El formulario de productos no cambia: estos datos se editan desde Inventario.
- Proveedor: lista de proveedores de la tienda.
- Venta / LineaVenta: una venta con uno o varios productos (Etapa 2).
- Ingreso / LineaIngreso: mercadería recibida de un proveedor (Etapa 3).
- Movimiento: el KARDEX. Cada cambio de stock queda guardado con su fecha,
  cantidad y el stock que quedó. Así se puede ver la historia de cada producto.

Ventas, movimientos y líneas guardan también los NOMBRES de la tienda y del
producto: si después se eliminan, la historia sigue siendo legible.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone

PRECIO = {"max_digits": 10, "decimal_places": 2}
no_negativo = MinValueValidator(Decimal("0"), message="No puede ser negativo.")


class FichaInventario(models.Model):
    producto = models.OneToOneField(
        "catalogo.Producto", on_delete=models.CASCADE, related_name="ficha", verbose_name="producto"
    )
    costo = models.DecimalField(
        "costo de compra (S/)", **PRECIO, null=True, blank=True, validators=[no_negativo],
        help_text="Cuánto te cuesta cada unidad. Sirve para calcular tu ganancia y el valor de tu inventario.",
    )
    stock_minimo = models.PositiveIntegerField(
        "stock mínimo", default=0,
        help_text="Te avisaremos cuando el stock llegue a esta cantidad. 0 = sin aviso.",
    )
    codigo = models.CharField(
        "código interno", max_length=40, blank=True,
        help_text="Opcional. El código que usas en tu tienda (SKU).",
    )
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        verbose_name = "ficha de inventario"
        verbose_name_plural = "fichas de inventario"

    def __str__(self):
        return f"Ficha de {self.producto}"


class Proveedor(models.Model):
    tienda = models.ForeignKey(
        "tiendas.Tienda", on_delete=models.CASCADE, related_name="proveedores", verbose_name="tienda"
    )
    nombre = models.CharField("nombre o razón social", max_length=120)
    ruc = models.CharField(
        "RUC", max_length=11, blank=True,
        validators=[RegexValidator(r"^\d{11}$", "El RUC tiene 11 dígitos.")],
    )
    telefono = models.CharField(
        "teléfono", max_length=15, blank=True,
        validators=[RegexValidator(r"^[\d +-]{6,15}$", "Escribe solo números (6 a 15 dígitos).")],
    )
    correo = models.EmailField("correo", blank=True)
    notas = models.TextField("notas", blank=True)
    creado = models.DateTimeField("registrado", auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "proveedor"
        verbose_name_plural = "proveedores"
        constraints = [
            models.UniqueConstraint(fields=["tienda", "nombre"], name="proveedor_unico_por_tienda"),
        ]

    def __str__(self):
        return self.nombre


class Venta(models.Model):
    class MetodoPago(models.TextChoices):
        EFECTIVO = "efectivo", "Efectivo"
        YAPE_PLIN = "yape_plin", "Yape / Plin"
        TARJETA = "tarjeta", "Tarjeta"
        TRANSFERENCIA = "transferencia", "Transferencia"
        OTRO = "otro", "Otro"

    tienda = models.ForeignKey(
        "tiendas.Tienda", on_delete=models.SET_NULL, null=True, blank=True, related_name="ventas", verbose_name="tienda"
    )
    tienda_nombre = models.CharField("tienda (nombre)", max_length=100)
    numero = models.PositiveIntegerField("número de venta")  # correlativo por tienda
    fecha = models.DateTimeField("fecha", default=timezone.now, db_index=True)
    metodo_pago = models.CharField("método de pago", max_length=15, choices=MetodoPago.choices, default=MetodoPago.EFECTIVO)
    cliente_nombre = models.CharField("cliente", max_length=120, blank=True)
    cliente_documento = models.CharField("DNI o RUC del cliente", max_length=11, blank=True)
    total = models.DecimalField("total (S/)", **PRECIO, default=Decimal("0"))
    nota = models.CharField("nota", max_length=255, blank=True)
    origen = models.CharField("origen", max_length=60, blank=True)  # p. ej. "Pedido #12" (ventas convertidas)
    anulada = models.BooleanField("anulada", default=False)
    motivo_anulacion = models.CharField("motivo de la anulación", max_length=255, blank=True)
    anulada_en = models.DateTimeField("anulada el", null=True, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ventas_registradas", verbose_name="registrada por",
    )

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "venta"
        verbose_name_plural = "ventas"
        constraints = [
            models.UniqueConstraint(fields=["tienda", "numero"], name="numero_de_venta_unico_por_tienda"),
        ]

    def __str__(self):
        return f"Venta N.° {self.numero:05d} · {self.tienda_nombre}"


class LineaVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="lineas", verbose_name="venta")
    producto = models.ForeignKey(
        "catalogo.Producto", on_delete=models.SET_NULL, null=True, blank=True, related_name="lineas_venta"
    )
    producto_nombre = models.CharField("producto (nombre)", max_length=200)
    cantidad = models.PositiveIntegerField("cantidad", validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField("precio unitario (S/)", **PRECIO, validators=[no_negativo])
    # Costo del producto al momento de vender: así la ganancia no cambia si después cambia el costo.
    costo_unitario = models.DecimalField("costo unitario (S/)", **PRECIO, null=True, blank=True)

    class Meta:
        verbose_name = "línea de venta"
        verbose_name_plural = "líneas de venta"

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad


class Ingreso(models.Model):
    tienda = models.ForeignKey(
        "tiendas.Tienda", on_delete=models.CASCADE, related_name="ingresos", verbose_name="tienda"
    )
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.SET_NULL, null=True, blank=True, related_name="ingresos", verbose_name="proveedor"
    )
    proveedor_nombre = models.CharField("proveedor (nombre)", max_length=120, blank=True)
    documento = models.CharField("factura o guía del proveedor", max_length=40, blank=True)
    fecha = models.DateTimeField("fecha", default=timezone.now, db_index=True)
    total = models.DecimalField("total (S/)", **PRECIO, default=Decimal("0"))
    nota = models.CharField("nota", max_length=255, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ingresos_registrados", verbose_name="registrado por",
    )

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "ingreso de mercadería"
        verbose_name_plural = "ingresos de mercadería"

    def __str__(self):
        return f"Ingreso del {self.fecha:%d/%m/%Y} · {self.proveedor_nombre or 'sin proveedor'}"


class LineaIngreso(models.Model):
    ingreso = models.ForeignKey(Ingreso, on_delete=models.CASCADE, related_name="lineas", verbose_name="ingreso")
    producto = models.ForeignKey(
        "catalogo.Producto", on_delete=models.SET_NULL, null=True, blank=True, related_name="lineas_ingreso"
    )
    producto_nombre = models.CharField("producto (nombre)", max_length=200)
    cantidad = models.PositiveIntegerField("cantidad", validators=[MinValueValidator(1)])
    costo_unitario = models.DecimalField("costo unitario (S/)", **PRECIO, validators=[no_negativo])

    class Meta:
        verbose_name = "línea de ingreso"
        verbose_name_plural = "líneas de ingreso"

    @property
    def subtotal(self):
        return self.costo_unitario * self.cantidad


class Movimiento(models.Model):
    """Una línea del kardex: un cambio en el stock de un producto."""

    class Tipo(models.TextChoices):
        INICIAL = "inicial", "Inventario inicial"
        VENTA = "venta", "Venta"
        ANULACION = "anulacion", "Venta anulada"
        INGRESO = "ingreso", "Ingreso de mercadería"
        AJUSTE = "ajuste", "Ajuste"
        CONTEO = "conteo", "Conteo físico"
        EDICION = "edicion", "Cambio al editar el producto"

    class Motivo(models.TextChoices):
        DANO = "dano", "Producto dañado"
        PERDIDA = "perdida", "Pérdida o robo"
        DEVOLUCION = "devolucion", "Devolución de un cliente"
        OTRO = "otro", "Otro"

    tienda = models.ForeignKey(
        "tiendas.Tienda", on_delete=models.SET_NULL, null=True, blank=True, related_name="movimientos", verbose_name="tienda"
    )
    tienda_nombre = models.CharField("tienda (nombre)", max_length=100)
    producto = models.ForeignKey(
        "catalogo.Producto", on_delete=models.SET_NULL, null=True, blank=True, related_name="movimientos", verbose_name="producto"
    )
    producto_nombre = models.CharField("producto (nombre)", max_length=200)
    tipo = models.CharField("tipo", max_length=10, choices=Tipo.choices)
    motivo = models.CharField("motivo", max_length=12, choices=Motivo.choices, blank=True)
    # Con signo: positivo entra al stock, negativo sale.
    cantidad = models.IntegerField("cantidad")
    stock_resultante = models.PositiveIntegerField("stock después")
    venta = models.ForeignKey(Venta, on_delete=models.SET_NULL, null=True, blank=True, related_name="movimientos")
    ingreso = models.ForeignKey(Ingreso, on_delete=models.SET_NULL, null=True, blank=True, related_name="movimientos")
    nota = models.CharField("nota", max_length=255, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="movimientos_inventario", verbose_name="registrado por",
    )
    fecha = models.DateTimeField("fecha", default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "movimiento de inventario"
        verbose_name_plural = "movimientos de inventario (kardex)"
        indexes = [
            models.Index(fields=["tienda", "fecha"], name="movimiento_tienda_fecha"),
            models.Index(fields=["producto", "fecha"], name="movimiento_producto_fecha"),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} · {self.producto_nombre} · {self.cantidad:+d}"

    @property
    def entrada(self):
        return self.cantidad if self.cantidad > 0 else None

    @property
    def salida(self):
        return -self.cantidad if self.cantidad < 0 else None
