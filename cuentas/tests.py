"""Pruebas de autenticación, roles y navegación."""

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from tiendas.tests import crear_tienda


class RolesTests(TestCase):
    def test_existen_los_roles_del_sistema(self):
        nombres = set(Group.objects.values_list("name", flat=True))
        self.assertTrue({"Administrador", "Tienda", "Cliente"} <= nombres)
        self.assertNotIn("Vendedor", nombres)

    def test_registro_de_cliente_asigna_rol_cliente(self):
        self.client.post(reverse("registro"), {
            "username": "cliente1",
            "first_name": "Ana",
            "last_name": "Quispe",
            "email": "ana@ejemplo.com",
            "password1": "ClaveSegura#2026",
            "password2": "ClaveSegura#2026",
        })
        usuario = User.objects.get(username="cliente1")
        self.assertTrue(usuario.groups.filter(name="Cliente").exists())

    def test_cliente_no_entra_al_panel_de_administracion(self):
        cliente = User.objects.create_user("cliente1", "c@ejemplo.com", "ClaveSegura#2026")
        self.client.force_login(cliente)
        respuesta = self.client.get(reverse("panel_admin"))
        self.assertEqual(respuesta.status_code, 403)

    def test_menu_de_tienda_muestra_mis_productos(self):
        tienda = crear_tienda()
        self.client.force_login(tienda.usuario)
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, reverse("catalogo:mis_productos"))

    def test_menu_de_visitante_no_muestra_mis_productos(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertNotContains(respuesta, reverse("catalogo:mis_productos"))
        self.assertContains(respuesta, reverse("tiendas:registro"))
