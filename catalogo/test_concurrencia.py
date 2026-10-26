"""
Pruebas de escenarios concurrentes en productos.
La concurrencia se simula con formularios abiertos antes de que otro cambio se guarde.
"""

from django.urls import reverse

from inventario.servicios import LineaPedida, registrar_venta
from tiendas.models import Tienda

from .models import Producto
from .tests import BaseCatalogo


class ConcurrenciaProductosTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.producto = self.crear_producto(stock=5)
        self.url = reverse("catalogo:editar", args=[self.producto.pk])
        self.client.force_login(self.tienda.usuario)

    def version_al_abrir(self):
        """La versión que lleva el formulario cuando la tienda abre 'Editar producto'."""
        respuesta = self.client.get(self.url)
        return respuesta.context["form"]["version"].value()

    def test_el_formulario_lleva_la_version(self):
        self.assertContains(self.client.get(self.url), 'name="version"')

    def test_editar_producto_desactualizado_no_sobrescribe(self):
        version_pestana_1 = self.version_al_abrir()
        version_pestana_2 = self.version_al_abrir()

        # La pestaña 2 guarda primero un precio nuevo.
        self.client.post(self.url, self.datos_formulario(nombre="Galaxy A15", precio="650.00", stock="5",
                                                         version=version_pestana_2))
        # La pestaña 1, abierta antes, intenta guardar con datos viejos.
        respuesta = self.client.post(self.url, self.datos_formulario(nombre="Galaxy A15", precio="700.00", stock="5",
                                                                     version=version_pestana_1))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "cambió mientras lo editabas")
        self.producto.refresh_from_db()
        self.assertEqual(str(self.producto.precio), "650.00")  # no se perdió el cambio de la pestaña 2

    def test_venta_mientras_se_edita_no_pierde_el_stock(self):
        version = self.version_al_abrir()  # la tienda abre el formulario con stock 5

        registrar_venta(self.tienda, self.tienda.usuario, [LineaPedida(self.producto.pk, 2)])  # se vende: stock 3

        respuesta = self.client.post(self.url, self.datos_formulario(nombre="Galaxy A15", stock="5", version=version))
        self.assertContains(respuesta, "cambió mientras lo editabas")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 3)  # antes de la corrección volvía a 5

    def test_con_la_version_al_dia_se_guarda_normal(self):
        version = self.version_al_abrir()
        respuesta = self.client.post(self.url, self.datos_formulario(nombre="Galaxy A15", precio="600.00", version=version))
        self.assertRedirects(respuesta, reverse("catalogo:mis_productos"))
        self.producto.refresh_from_db()
        self.assertEqual(str(self.producto.precio), "600.00")

    def test_eliminar_producto_vendido_conserva_la_venta(self):
        venta = registrar_venta(self.tienda, self.tienda.usuario, [LineaPedida(self.producto.pk, 1)])
        self.client.post(reverse("catalogo:eliminar", args=[self.producto.pk]))
        self.assertFalse(Producto.objects.filter(pk=self.producto.pk).exists())
        linea = venta.lineas.get()
        self.assertIsNone(linea.producto)
        self.assertEqual(linea.producto_nombre, "Galaxy A15")

    def test_tienda_suspendida_mientras_edita_no_guarda(self):
        version = self.version_al_abrir()
        Tienda.objects.filter(pk=self.tienda.pk).update(estado=Tienda.Estado.SUSPENDIDA)  # el admin la suspende

        respuesta = self.client.post(self.url, self.datos_formulario(nombre="Otro nombre", version=version))
        self.assertRedirects(respuesta, reverse("tiendas:panel"))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, "Galaxy A15")
