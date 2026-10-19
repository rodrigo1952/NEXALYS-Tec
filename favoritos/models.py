from django.conf import settings
from django.db import models


class Favorito(models.Model):
    """
    Producto que un Cliente guardó para verlo después.

    Reglas de negocio:
    - Solo los usuarios con rol Cliente tienen favoritos.
    - Un producto aparece una sola vez en la lista de cada cliente.
    - Si la tienda elimina el producto, el favorito se borra solo (CASCADE).
    - "Bajó de precio" compara el precio actual con el precio que tenía al guardarlo.
    - Los avisos nuevos (contador del menú) comparan con lo que el cliente vio
      la última vez que abrió "Mis favoritos".
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favoritos",
        verbose_name="cliente",
    )
    producto = models.ForeignKey(
        "catalogo.Producto",
        on_delete=models.CASCADE,
        related_name="favoritos",
        verbose_name="producto",
    )
    precio_guardado = models.DecimalField("precio al guardarlo", max_digits=8, decimal_places=2)
    precio_visto = models.DecimalField("precio en la última revisión", max_digits=8, decimal_places=2)
    agotado_visto = models.BooleanField("agotado en la última revisión", default=False)
    creado = models.DateTimeField("guardado el", auto_now_add=True)

    class Meta:
        ordering = ["-creado"]
        verbose_name = "favorito"
        verbose_name_plural = "favoritos"
        constraints = [
            models.UniqueConstraint(fields=["usuario", "producto"], name="favorito_unico_por_usuario"),
        ]

    def __str__(self):
        return f"{self.usuario} ❤ {self.producto}"

    @classmethod
    def guardar(cls, usuario, producto):
        """Guarda el producto en favoritos (sin duplicar). Devuelve (favorito, creado)."""
        return cls.objects.get_or_create(
            usuario=usuario,
            producto=producto,
            defaults={
                "precio_guardado": producto.precio,
                "precio_visto": producto.precio,
                "agotado_visto": producto.agotado,
            },
        )

    @property
    def disponible(self):
        """El producto sigue publicado y su tienda está activa."""
        return self.producto.activo and self.producto.tienda.esta_activa

    @property
    def bajo_de_precio(self):
        return self.disponible and self.producto.precio < self.precio_guardado

    @property
    def volvio_a_tener_stock(self):
        return self.disponible and self.agotado_visto and not self.producto.agotado

    def marcar_revisado(self):
        """Recuerda lo que el cliente acaba de ver (no guarda en la base de datos)."""
        self.precio_visto = self.producto.precio
        self.agotado_visto = self.producto.agotado
