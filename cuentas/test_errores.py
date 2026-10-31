"""Páginas de error sobrias: sin buscador, secciones ni categorías, con botones según quién es."""

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from tiendas.tests import crear_tienda

CLAVE = "ClaveSegura#2026"


class PaginaSinPermisoTests(TestCase):
    def setUp(self):
        self.tienda = crear_tienda()

    def test_tienda_en_la_consola(self):
        self.client.force_login(self.tienda.usuario)
        respuesta = self.client.get(reverse("administracion:usuarios"))
        self.assertEqual(respuesta.status_code, 403)
        self.assertContains(respuesta, "Acceso restringido", status_code=403)
        self.assertContains(respuesta, "equipo de administración", status_code=403)
        self.assertContains(respuesta, "Entraste como <strong>tienda1</strong> (tienda)", status_code=403)
        self.assertContains(respuesta, f'href="{reverse("catalogo:mis_productos")}" class="btn btn-primary"', status_code=403)
        self.assertContains(respuesta, "Entrar con otra cuenta", status_code=403)
        self.assertContains(respuesta, f'value="{reverse("login")}?next=/administracion/usuarios/"', status_code=403)
        for parte in ('id="buscar-menu"', 'class="barra-categorias"', 'menu-secciones', 'class="pie-marca'):
            self.assertNotContains(respuesta, parte, status_code=403)

    def test_cliente_en_la_zona_de_la_tienda(self):
        cliente = User.objects.create_user("cliente1", "c@ejemplo.com", CLAVE)
        cliente.groups.add(Group.objects.get(name="Cliente"))
        self.client.force_login(cliente)
        respuesta = self.client.get(reverse("panel_admin"))
        self.assertContains(respuesta, f'href="{reverse("inicio")}" class="btn btn-primary"', status_code=403)
        self.assertContains(respuesta, "(cliente)", status_code=403)

    def test_entrar_con_otra_cuenta_lleva_al_login(self):
        self.client.force_login(self.tienda.usuario)
        destino = f'{reverse("login")}?next=/administracion/usuarios/'
        respuesta = self.client.post(reverse("logout"), {"next": destino})
        self.assertRedirects(respuesta, destino, fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)


class PaginaNoEncontradaTests(TestCase):
    def test_404_sobria(self):
        respuesta = self.client.get("/no-existe/")
        self.assertContains(respuesta, "No encontramos esta página", status_code=404)
        self.assertNotContains(respuesta, 'class="barra-categorias"', status_code=404)
        self.assertNotContains(respuesta, 'id="buscar-menu"', status_code=404)


class TablaDeTiendasTests(TestCase):
    def test_el_logo_y_el_nombre_abren_la_tienda(self):
        tienda = crear_tienda()
        admin = User.objects.create_user("jefe", "j@ejemplo.com", CLAVE)
        admin.groups.add(Group.objects.get_or_create(name="Administrador")[0])
        self.client.force_login(admin)
        respuesta = self.client.get(reverse("administracion:tiendas"))
        self.assertContains(respuesta, f'<a href="{reverse("administracion:tienda_detalle", args=[tienda.pk])}" class="enlace-fila">')
        self.assertNotContains(respuesta, ">Ver</a>")
