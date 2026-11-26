"""Nov 2026: el precio de oferta va en rojo oscuro (#C62828); el precio normal sigue en azul."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.staticfiles import finders
from django.urls import reverse
from django.utils import timezone

from .tests import BaseCatalogo


class PrecioDeOfertaEnRojoTests(BaseCatalogo):
    def test_producto_sin_oferta_no_lleva_el_rojo(self):
        self.crear_producto(nombre="Impresora sin oferta", precio=Decimal("789.00"))
        self.assertNotContains(self.client.get(reverse("catalogo:catalogo")), "precio--oferta")

    def test_tarjeta_con_oferta_lleva_el_rojo(self):
        self.crear_producto(precio=Decimal("250.00"), precio_oferta=Decimal("199.99"))
        self.assertContains(self.client.get(reverse("catalogo:catalogo")), "precio--oferta")

    def test_detalle_con_precio_y_aviso_en_rojo(self):
        producto = self.crear_producto(
            precio=Decimal("250.00"),
            precio_oferta=Decimal("199.99"),
            oferta_hasta=timezone.localdate() + timedelta(days=5),
        )
        respuesta = self.client.get(reverse("catalogo:detalle", args=[producto.pk]))
        self.assertContains(respuesta, "precio--oferta")
        self.assertContains(respuesta, 'class="small aviso-oferta mb-2"')
        self.assertContains(respuesta, "bi-tag-fill")

    def test_mis_productos_con_oferta_en_rojo(self):
        self.crear_producto(precio=Decimal("250.00"), precio_oferta=Decimal("199.99"))
        self.client.force_login(self.tienda.usuario)
        self.assertContains(self.client.get(reverse("catalogo:mis_productos")), "precio--oferta")

    def test_el_color_esta_en_la_hoja_de_estilos(self):
        with open(finders.find("css/marca.css"), encoding="utf-8") as archivo:
            css = archivo.read()
        self.assertIn(".tarjeta-producto__precio .precio.precio--oferta { color: #C62828 !important; }", css)
        self.assertIn("body.fondo-marca .aviso-oferta {", css)
