"""Pruebas del CRUD de categorías y marcas (CU-07), solo para el Administrador."""

from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from tiendas.tests import crear_tienda

from .models import Categoria, Marca, Producto


class GestionCategoriasMarcasTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("jefe", "jefe@ejemplo.com", "ClaveSegura#2026")
        self.admin.groups.add(Group.objects.get(name="Administrador"))
        self.client.force_login(self.admin)

    def test_administrador_ve_el_listado(self):
        respuesta = self.client.get(reverse("catalogo:gestion_lista", args=["categorias"]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Celulares")

    def test_crear_categoria(self):
        self.client.post(reverse("catalogo:gestion_crear", args=["categorias"]), {"nombre": "Tablets", "activa": "on"})
        self.assertTrue(Categoria.objects.filter(nombre="Tablets").exists())

    def test_crear_marca(self):
        self.client.post(reverse("catalogo:gestion_crear", args=["marcas"]), {"nombre": "Huawei", "activa": "on"})
        self.assertTrue(Marca.objects.filter(nombre="Huawei").exists())

    def test_nombre_repetido_sin_importar_mayusculas_se_rechaza(self):
        respuesta = self.client.post(reverse("catalogo:gestion_crear", args=["marcas"]), {"nombre": "samsung"})
        self.assertIn("nombre", respuesta.context["form"].errors)

    def test_nombre_muy_corto_se_rechaza(self):
        respuesta = self.client.post(reverse("catalogo:gestion_crear", args=["categorias"]), {"nombre": "A"})
        self.assertIn("nombre", respuesta.context["form"].errors)

    def test_editar_y_desactivar_categoria(self):
        categoria = Categoria.objects.create(nombre="Drones")
        self.client.post(reverse("catalogo:gestion_editar", args=["categorias", categoria.pk]), {"nombre": "Drones y cámaras"})
        categoria.refresh_from_db()
        self.assertEqual(categoria.nombre, "Drones y cámaras")
        self.assertFalse(categoria.activa)

    def test_eliminar_categoria_sin_productos(self):
        categoria = Categoria.objects.create(nombre="Consolas")
        self.client.post(reverse("catalogo:gestion_eliminar", args=["categorias", categoria.pk]))
        self.assertFalse(Categoria.objects.filter(pk=categoria.pk).exists())

    def test_no_se_elimina_marca_con_productos(self):
        marca = Marca.objects.get(nombre="Samsung")
        Producto.objects.create(
            tienda=crear_tienda(), categoria=Categoria.objects.get(nombre="Celulares"),
            marca=marca, nombre="Galaxy A15", precio=Decimal("699"), stock=1,
        )
        self.client.post(reverse("catalogo:gestion_eliminar", args=["marcas", marca.pk]))
        self.assertTrue(Marca.objects.filter(pk=marca.pk).exists())

    def test_tipo_inexistente_responde_404(self):
        respuesta = self.client.get(reverse("catalogo:gestion_lista", args=["usuarios"]))
        self.assertEqual(respuesta.status_code, 404)


class PermisosGestionTests(TestCase):
    def test_tienda_no_puede_gestionar_categorias(self):
        tienda = crear_tienda()
        self.client.force_login(tienda.usuario)
        respuesta = self.client.get(reverse("catalogo:gestion_lista", args=["categorias"]))
        self.assertEqual(respuesta.status_code, 403)

    def test_visitante_es_enviado_al_login(self):
        respuesta = self.client.get(reverse("catalogo:gestion_lista", args=["marcas"]))
        self.assertEqual(respuesta.status_code, 302)

    def test_categoria_inactiva_no_aparece_al_crear_producto(self):
        Categoria.objects.create(nombre="Descontinuada", activa=False)
        tienda = crear_tienda()
        self.client.force_login(tienda.usuario)
        respuesta = self.client.get(reverse("catalogo:crear"))
        self.assertNotContains(respuesta, "Descontinuada")
