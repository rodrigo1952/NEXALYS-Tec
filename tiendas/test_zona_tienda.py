"""Cuenta de tienda: entra a «Mis productos», su menú va primero y ahí no hay barra de categorías."""

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .tests import crear_tienda

CLAVE = "ClaveSegura#2026"


class ZonaDeLaTiendaTests(TestCase):
    def setUp(self):
        self.tienda = crear_tienda()

    def entrar(self, usuario, tipo, **extra):
        url = reverse("login")
        if extra.get("next"):
            url += f"?next={extra['next']}"
        datos = {"username": usuario, "password": CLAVE, "tipo": tipo}
        if extra.get("next"):
            datos["next"] = extra["next"]
        return self.client.post(url, datos)

    def test_la_tienda_entra_a_mis_productos(self):
        self.assertRedirects(self.entrar("tienda1", "tienda"), reverse("catalogo:mis_productos"), fetch_redirect_response=False)

    def test_si_venia_de_un_enlace_vuelve_ahi(self):
        destino = reverse("inventario:ventas")
        self.assertRedirects(self.entrar("tienda1", "tienda", next=destino), destino, fetch_redirect_response=False)

    def test_el_cliente_sigue_entrando_al_inicio(self):
        cliente = User.objects.create_user("cliente1", "c@ejemplo.com", CLAVE)
        cliente.groups.add(Group.objects.get(name="Cliente"))
        self.assertRedirects(self.entrar("cliente1", "cliente"), reverse("inicio"), fetch_redirect_response=False)

    def test_menu_mis_productos_inicio_catalogo(self):
        self.client.force_login(self.tienda.usuario)
        html = self.client.get(reverse("inicio")).content.decode()
        menu = html[html.index('class="navbar-nav menu-secciones'):]
        mis = menu.index(f'href="{reverse("catalogo:mis_productos")}"')
        inicio = menu.index(f'href="{reverse("inicio")}"')
        catalogo = menu.index(f'href="{reverse("catalogo:catalogo")}"')
        self.assertLess(mis, inicio)
        self.assertLess(inicio, catalogo)

    def test_sin_categorias_en_la_zona_de_trabajo(self):
        self.client.force_login(self.tienda.usuario)
        for url in (reverse("catalogo:mis_productos"), reverse("catalogo:crear"), reverse("inventario:ventas"),
                    reverse("inventario:ingresos"), reverse("inventario:resumen")):
            with self.subTest(url=url):
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, 200)
                self.assertNotContains(respuesta, 'class="barra-categorias"')
        self.assertContains(self.client.get(reverse("inicio")), 'class="barra-categorias"')
        self.assertContains(self.client.get(reverse("catalogo:catalogo")), 'class="barra-categorias"')
