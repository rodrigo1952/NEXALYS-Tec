"""
Pruebas de escenarios concurrentes en productos.
La concurrencia se simula con formularios abiertos antes de que otro cambio se guarde.
"""

from unittest import mock

from django.db.models import ProtectedError
from django.urls import reverse

from pedidos.models import Pedido
from pedidos.servicios import registrar_pedido
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

    def test_pedido_mientras_se_edita_no_pierde_el_stock(self):
        version = self.version_al_abrir()  # la tienda abre el formulario con stock 5

        registrar_pedido(Pedido(
            tienda=self.tienda, producto=self.producto, cantidad=2,
            cliente_nombre="Ana Quispe", cliente_telefono="987654321",
        ))  # mientras tanto se vende: stock 3

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

    def test_eliminar_producto_con_pedido_recien_registrado(self):
        # La revisión "¿tiene pedidos?" pasa, pero justo antes de borrar llega un pedido.
        url = reverse("catalogo:eliminar", args=[self.producto.pk])
        with mock.patch.object(Producto, "delete", side_effect=ProtectedError("tiene pedidos", set())):
            respuesta = self.client.post(url, follow=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "se le acaba de registrar un pedido")
        self.assertTrue(Producto.objects.filter(pk=self.producto.pk).exists())

    def test_tienda_suspendida_mientras_edita_no_guarda(self):
        version = self.version_al_abrir()
        Tienda.objects.filter(pk=self.tienda.pk).update(estado=Tienda.Estado.SUSPENDIDA)  # el admin la suspende

        respuesta = self.client.post(self.url, self.datos_formulario(nombre="Otro nombre", version=version))
        self.assertRedirects(respuesta, reverse("tiendas:panel"))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, "Galaxy A15")
