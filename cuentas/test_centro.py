"""Centro de cuenta: menú lateral y cabecera simple, sin Inicio/Catálogo ni la barra de categorías."""

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from tiendas.tests import crear_tienda

CLAVE = "ClaveSegura#2026"


class CentroDeCuentaTests(TestCase):
    def setUp(self):
        self.tienda = crear_tienda()
        self.client.force_login(self.tienda.usuario)

    def paginas(self):
        return ("mi_cuenta", "editar_datos", "password_change", "ayuda", "privacidad", "tiendas:panel", "tiendas:editar")

    def test_las_paginas_de_la_cuenta_usan_el_menu_lateral(self):
        for nombre in self.paginas():
            with self.subTest(pagina=nombre):
                respuesta = self.client.get(reverse(nombre))
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, 'class="centro-cuenta__menu"')
                self.assertContains(respuesta, "Volver a la página")
                # Sin buscador, sin Inicio/Catálogo y sin la barra de categorías.
                self.assertNotContains(respuesta, "barra-categorias")
                self.assertNotContains(respuesta, 'name="q"')
                self.assertNotContains(respuesta, f'href="{reverse("catalogo:catalogo")}" class="nav-link')

    def test_la_seccion_actual_queda_marcada(self):
        respuesta = self.client.get(reverse("tiendas:panel"))
        self.assertContains(respuesta, f'<a href="{reverse("tiendas:panel")}" class="activo" aria-current="page">', html=False)
        respuesta = self.client.get(reverse("ayuda"))
        self.assertContains(respuesta, f'<a href="{reverse("ayuda")}" class="activo" aria-current="page">', html=False)

    def test_datos_de_mi_tienda_con_sus_numeros(self):
        respuesta = self.client.get(reverse("tiendas:panel"))
        self.assertContains(respuesta, "<title>Datos de mi tienda | NEXALYS Tec</title>", html=False)
        self.assertContains(respuesta, 'class="numeros-tienda mt-3"')
        self.assertContains(respuesta, f'href="{reverse("catalogo:mis_productos")}" class="enlace-accion">Ver en Mis productos')
        self.assertContains(respuesta, "Editar datos, logo y horario")
        self.assertContains(respuesta, "Horario de atención")

    def test_el_resto_de_la_pagina_sigue_igual(self):
        # El catálogo y el inicio conservan la cabecera completa.
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, "barra-categorias")
        self.assertNotContains(respuesta, "centro-cuenta__menu")

    def test_ayuda_con_temas_y_privacidad_con_indice(self):
        respuesta = self.client.get(reverse("ayuda"))
        self.assertContains(respuesta, 'href="#tema-tiendas"')
        self.assertContains(respuesta, 'id="tema-cuenta"')
        self.assertNotContains(respuesta, 'href="#tema-clientes"')  # la tienda no ve las de clientes
        respuesta = self.client.get(reverse("privacidad"))
        for ancla in ("datos", "derechos", "plazos", "reglas"):
            self.assertContains(respuesta, f'href="#{ancla}"')
            self.assertContains(respuesta, f'id="{ancla}"')

    def test_el_cliente_ve_sus_accesos(self):
        cliente = User.objects.create_user("cliente1", "c@ejemplo.com", CLAVE)
        cliente.groups.add(Group.objects.get(name="Cliente"))
        self.client.force_login(cliente)
        respuesta = self.client.get(reverse("mi_cuenta"))
        self.assertContains(respuesta, f'href="{reverse("favoritos:lista")}"')
        self.assertNotContains(respuesta, "Datos de mi tienda")
        self.assertContains(self.client.get(reverse("ayuda")), 'href="#tema-clientes"')

    def test_el_visitante_puede_leer_ayuda_y_privacidad(self):
        self.client.logout()
        for nombre in ("ayuda", "privacidad"):
            respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 200)
            self.assertNotContains(respuesta, f'href="{reverse("mi_cuenta")}"')
            self.assertContains(respuesta, f'href="{reverse("login")}" class="btn btn-primary w-100 mt-3"')
