"""La marca "Circuito" (azul marino y cian) se carga en todas las páginas."""
from django.test import TestCase
from django.urls import reverse


class MarcaTests(TestCase):
    def test_inicio_carga_la_marca(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, "css/marca.css")
        self.assertContains(respuesta, "img/favicon.svg")
        self.assertContains(respuesta, "Space+Grotesk")
        self.assertContains(respuesta, 'class="navbar navbar-expand-lg navbar-dark navbar-marca"')
        self.assertContains(respuesta, 'class="logo-marca"')
        self.assertContains(respuesta, "portada-marca")

    def test_boton_registrar_tienda_es_de_accion(self):
        # Sobre el menú azul marino, un botón azul no se vería: debe ser cian.
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, 'class="btn btn-acento btn-sm ms-lg-2"')

    def test_login_muestra_el_logo_sobre_fondo_claro(self):
        respuesta = self.client.get(reverse("login"))
        self.assertContains(respuesta, "logo-marca logo-marca--claro")


class MenuConBuscadorTests(TestCase):
    """Menú de dos filas: buscador al centro y secciones según el tipo de usuario."""

    def setUp(self):
        from django.contrib.auth.models import Group, User
        from tiendas.tests import crear_tienda
        self.cliente = User.objects.create_user("cliente1", "c@ejemplo.com", "ClaveSegura#2026")
        self.cliente.groups.add(Group.objects.get(name="Cliente"))
        self.admin = User.objects.create_superuser("admin", "a@ejemplo.com", "ClaveSegura#2026")
        self.tienda = crear_tienda()

    def secciones(self, usuario=None):
        if usuario:
            self.client.force_login(usuario)
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, 'id="cabecera"')
        self.assertContains(respuesta, 'id="buscar-menu"')
        self.assertContains(respuesta, f'action="{reverse("catalogo:catalogo")}" role="search"')
        return respuesta

    def test_visitante(self):
        respuesta = self.secciones()
        self.assertContains(respuesta, "Iniciar sesión")
        self.assertNotContains(respuesta, reverse("favoritos:lista"))

    def test_cliente_ve_mis_favoritos(self):
        respuesta = self.secciones(self.cliente)
        self.assertContains(respuesta, f'href="{reverse("favoritos:lista")}"')
        self.assertNotContains(respuesta, reverse("panel_admin"))

    def test_admin_ve_administracion(self):
        respuesta = self.secciones(self.admin)
        self.assertContains(respuesta, f'href="{reverse("panel_admin")}"')
        self.assertNotContains(respuesta, reverse("favoritos:lista"))

    def test_tienda_ve_sus_secciones(self):
        respuesta = self.secciones(self.tienda.usuario)
        for nombre in ("tiendas:panel", "catalogo:mis_productos"):
            self.assertContains(respuesta, f'href="{reverse(nombre)}"')
        self.assertNotContains(respuesta, ">Pedidos<")  # la sección Pedidos se retiró (Etapa 5)

    def test_buscador_conserva_lo_buscado_en_el_catalogo(self):
        respuesta = self.client.get(reverse("catalogo:catalogo"), {"q": "laptop"})
        self.assertContains(respuesta, 'value="laptop"')
