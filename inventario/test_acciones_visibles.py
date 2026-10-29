"""
Acciones visibles: "Volver", los atajos para crear y los enlaces "ver más" se dibujan
como botones o enlaces destacados (clases de marca.css), no como texto pequeño.
"""

from decimal import Decimal

from django.urls import reverse

from catalogo.tests import BaseCatalogo

from .servicios import LineaPedida, LineaRecibida, registrar_ingreso, registrar_venta


class AccionesVisiblesTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.producto = self.crear_producto(nombre="Galaxy A15", stock=4)
        self.client.force_login(self.tienda.usuario)

    def assertBotonVolver(self, url, destino):
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, f'href="{destino}" class="btn-volver"')
        self.assertNotContains(respuesta, 'class="small">&larr;')

    def test_pantallas_de_la_tienda_usan_el_boton_volver(self):
        venta = registrar_venta(self.tienda, self.tienda.usuario, [LineaPedida(self.producto.pk, 1)])
        ingreso = registrar_ingreso(self.tienda, self.tienda.usuario,
                                    [LineaRecibida(self.producto.pk, 2, Decimal("500"))])
        casos = [
            (reverse("inventario:ingreso_nuevo"), reverse("inventario:ingresos")),
            (reverse("inventario:venta_nueva"), reverse("inventario:ventas")),
            (reverse("inventario:ajuste_nuevo"), reverse("inventario:ajustes")),
            (reverse("inventario:conteo"), reverse("inventario:ajustes")),
            (reverse("inventario:kardex", args=[self.producto.pk]), reverse("catalogo:mis_productos")),
            (reverse("inventario:venta_detalle", args=[venta.pk]), reverse("inventario:ventas")),
            (reverse("inventario:ingreso_detalle", args=[ingreso.pk]), reverse("inventario:ingresos")),
            (reverse("inventario:proveedor_crear"), reverse("inventario:proveedores")),
            (reverse("tiendas:editar"), reverse("tiendas:panel")),
            (reverse("catalogo:detalle", args=[self.producto.pk]), reverse("catalogo:catalogo")),
        ]
        for url, destino in casos:
            with self.subTest(url=url):
                self.assertBotonVolver(url, destino)

    def test_nuevo_ingreso_tiene_atajos_visibles_para_crear(self):
        respuesta = self.client.get(reverse("inventario:ingreso_nuevo"))
        self.assertContains(respuesta, 'class="atajo')
        self.assertContains(respuesta, f'href="{reverse("catalogo:crear")}?volver=ingreso" class="btn btn-sm btn-primary"')
        self.assertContains(respuesta, f'href="{reverse("inventario:proveedor_crear")}" class="btn btn-outline-primary"')
        self.assertNotContains(respuesta, "Créalo primero")

    def test_nueva_venta_tiene_el_atajo_para_crear_producto(self):
        respuesta = self.client.get(reverse("inventario:venta_nueva"))
        self.assertContains(respuesta, f'href="{reverse("catalogo:crear")}?volver=venta" class="btn btn-sm btn-primary"')

    def test_el_kardex_destaca_ver_venta(self):
        registrar_venta(self.tienda, self.tienda.usuario, [LineaPedida(self.producto.pk, 1)])
        respuesta = self.client.get(reverse("inventario:kardex", args=[self.producto.pk]))
        self.assertContains(respuesta, 'class="enlace-accion ms-1">Ver venta</a>')

    def test_mis_productos_destaca_ver_numeros_en_resumen(self):
        respuesta = self.client.get(reverse("catalogo:mis_productos"))
        self.assertContains(respuesta, 'class="enlace-accion ms-auto">Ver números en Resumen</a>')

    def test_quitar_busqueda_es_un_boton(self):
        respuesta = self.client.get(reverse("inventario:ventas"), {"q": "Galaxy"})
        self.assertContains(respuesta, 'class="btn btn-outline-secondary">✕ Quitar búsqueda</a>')

    def test_el_estilo_existe_en_marca_css(self):
        from django.contrib.staticfiles import finders

        with open(finders.find("css/marca.css"), encoding="utf-8") as archivo:
            css = archivo.read()
        for clase in (".btn-volver", ".atajo", ".enlace-accion"):
            self.assertIn(clase, css)
