"""Precio de compra en el formulario de producto y creación de productos desde un ingreso o una venta."""

from decimal import Decimal

from django.urls import reverse

from catalogo.models import Producto
from catalogo.tests import BaseCatalogo

from . import servicios
from .models import FichaInventario
from .servicios import LineaRecibida


class PrecioDeCompraTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.tienda.usuario)

    def test_compra_y_venta_en_la_misma_fila(self):
        respuesta = self.client.get(reverse("catalogo:crear"))
        self.assertContains(respuesta, "Precio de compra (S/)")
        self.assertContains(respuesta, "Precio de venta (S/)")
        html = respuesta.content.decode()
        fila = html.index('<div class="row g-3 mb-3">')
        self.assertLess(fila, html.index('name="precio_compra"'))
        self.assertLess(html.index('name="precio_compra"'), html.index('name="precio"'))

    def test_crear_con_precio_de_compra_lo_guarda_en_la_ficha(self):
        self.client.post(reverse("catalogo:crear"), self.datos_formulario(precio_compra="750.00"))
        producto = Producto.objects.get(nombre="Galaxy A25")
        self.assertEqual(FichaInventario.objects.get(producto=producto).costo, Decimal("750.00"))

    def test_el_precio_de_compra_es_opcional(self):
        self.client.post(reverse("catalogo:crear"), self.datos_formulario())
        producto = Producto.objects.get(nombre="Galaxy A25")
        self.assertFalse(FichaInventario.objects.filter(producto=producto, costo__isnull=False).exists())

    def test_al_editar_muestra_el_costo_promedio_y_no_lo_pisa(self):
        producto = self.crear_producto(nombre="Galaxy A25", stock=2)
        FichaInventario.objects.create(producto=producto, costo=Decimal("100.00"))
        servicios.registrar_ingreso(self.tienda, self.tienda.usuario, [LineaRecibida(producto.pk, 3, Decimal("120.00"))])
        url = reverse("catalogo:editar", args=[producto.pk])
        self.assertEqual(self.client.get(url).context["form"]["precio_compra"].value(), Decimal("112.00"))
        producto.refresh_from_db()
        # Guardar sin tocar el precio de compra no cambia el costo.
        datos = self.datos_formulario(stock="5", precio_compra="112.00", version=producto.actualizado.isoformat())
        self.client.post(url, datos)
        self.assertEqual(FichaInventario.objects.get(producto=producto).costo, Decimal("112.00"))
        # Cambiarlo a mano sí lo cambia (es el mismo dato que la ficha).
        producto.refresh_from_db()
        datos.update(precio_compra="110.00", version=producto.actualizado.isoformat())
        self.client.post(url, datos)
        self.assertEqual(FichaInventario.objects.get(producto=producto).costo, Decimal("110.00"))

    def test_marca_los_productos_sin_precio_de_compra(self):
        con_costo = self.crear_producto(nombre="Con costo")
        FichaInventario.objects.create(producto=con_costo, costo=Decimal("10"))
        self.crear_producto(nombre="Sin costo")
        respuesta = self.client.get(reverse("catalogo:mis_productos"))
        self.assertContains(respuesta, "Falta precio de compra", count=1)
        self.assertEqual(respuesta.context["resumen"]["sin_costo"], 1)
        filtrado = self.client.get(reverse("catalogo:mis_productos"), {"sin_costo": "1"})
        self.assertEqual([p.nombre for p in filtrado.context["pagina"]], ["Sin costo"])

    def test_el_aviso_solo_lo_ve_la_tienda(self):
        producto = self.crear_producto(nombre="Sin costo")
        self.client.logout()
        respuesta = self.client.get(reverse("catalogo:detalle", args=[producto.pk]))
        self.assertNotContains(respuesta, "Falta precio de compra")
        self.client.force_login(self.otra_tienda.usuario)
        self.assertNotContains(self.client.get(reverse("catalogo:mis_productos")), "Falta precio de compra")


class CrearProductoDesdeIngresoTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.tienda.usuario)

    def test_enlaces_en_ingreso_y_venta(self):
        self.assertContains(self.client.get(reverse("inventario:ingreso_nuevo")), "?volver=ingreso")
        self.assertContains(self.client.get(reverse("inventario:venta_nueva")), "?volver=venta")

    def test_desde_un_ingreso_vuelve_con_el_producto_elegido(self):
        url = f"{reverse('catalogo:crear')}?volver=ingreso"
        self.assertContains(self.client.get(url), "Deja el <strong>stock en 0</strong>")
        respuesta = self.client.post(url, self.datos_formulario(stock="0"))
        producto = Producto.objects.get(nombre="Galaxy A25")
        destino = f"{reverse('inventario:ingreso_nuevo')}?producto={producto.pk}"
        self.assertRedirects(respuesta, destino)
        formulario = self.client.get(destino)
        self.assertEqual(formulario.context["lineas"].forms[0]["producto"].value(), producto.pk)

    def test_desde_una_venta_vuelve_a_la_venta(self):
        respuesta = self.client.post(f"{reverse('catalogo:crear')}?volver=venta", self.datos_formulario(stock="3"))
        producto = Producto.objects.get(nombre="Galaxy A25")
        self.assertRedirects(respuesta, f"{reverse('inventario:venta_nueva')}?producto={producto.pk}")

    def test_volver_desconocido_va_a_mis_productos(self):
        respuesta = self.client.post(f"{reverse('catalogo:crear')}?volver=https://otro.com", self.datos_formulario())
        self.assertRedirects(respuesta, reverse("catalogo:mis_productos"))

    def test_no_preselecciona_productos_de_otra_tienda(self):
        ajeno = self.crear_producto(tienda=self.otra_tienda, nombre="Ajeno")
        respuesta = self.client.get(reverse("inventario:ingreso_nuevo"), {"producto": ajeno.pk})
        self.assertIsNone(respuesta.context["lineas"].forms[0]["producto"].value())
