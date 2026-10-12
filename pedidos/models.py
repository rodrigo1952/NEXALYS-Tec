from django.core.validators import MinValueValidator
from django.db import models

from tiendas.models import validar_whatsapp


class Pedido(models.Model):
    """CU-08 Gestionar pedidos: la tienda registra lo que le compran por WhatsApp."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        CONFIRMADO = "confirmado", "Confirmado"
        ENTREGADO = "entregado", "Entregado"
        CANCELADO = "cancelado", "Cancelado"

    # Regla de negocio: el pedido avanza en este orden; "entregado" y "cancelado" son finales.
    TRANSICIONES = {
        Estado.PENDIENTE: [Estado.CONFIRMADO, Estado.CANCELADO],
        Estado.CONFIRMADO: [Estado.ENTREGADO, Estado.CANCELADO],
        Estado.ENTREGADO: [],
        Estado.CANCELADO: [],
    }

    tienda = models.ForeignKey(
        "tiendas.Tienda",
        on_delete=models.CASCADE,
        related_name="pedidos",
        verbose_name="tienda",
    )
    producto = models.ForeignKey(
        "catalogo.Producto",
        on_delete=models.PROTECT,
        related_name="pedidos",
        verbose_name="producto",
    )
    cliente_nombre = models.CharField("nombre del cliente", max_length=100)
    cliente_telefono = models.CharField(
        "celular del cliente",
        max_length=9,
        validators=[validar_whatsapp],
        help_text="9 dígitos. Ejemplo: 987654321",
    )
    cantidad = models.PositiveIntegerField(
        "cantidad",
        validators=[MinValueValidator(1, message="La cantidad mínima es 1.")],
    )
    precio_unitario = models.DecimalField("precio unitario (S/)", max_digits=8, decimal_places=2)
    estado = models.CharField(
        "estado",
        max_length=12,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    observacion = models.TextField("observación", blank=True)
    creado = models.DateTimeField("registrado", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        ordering = ["-creado"]
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"

    def __str__(self):
        return f"Pedido #{self.pk} - {self.cliente_nombre}"

    @property
    def total(self):
        return self.precio_unitario * self.cantidad

    @property
    def editable(self):
        """Solo se edita mientras está pendiente."""
        return self.estado == self.Estado.PENDIENTE

    @property
    def eliminable(self):
        """Los pedidos confirmados o entregados forman parte del historial de ventas."""
        return self.estado in (self.Estado.PENDIENTE, self.Estado.CANCELADO)

    def estados_siguientes(self):
        return [self.Estado(valor) for valor in self.TRANSICIONES[self.Estado(self.estado)]]

    def puede_cambiar_a(self, nuevo_estado):
        return nuevo_estado in self.TRANSICIONES[self.Estado(self.estado)]
