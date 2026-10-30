"""Nuevo inicio de sesión (Soy cliente / Soy tienda), logo animado de Inicio y ventana de cerrar sesión."""
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from tiendas.tests import crear_tienda

CLAVE = "ClaveSegura#2026"


class IngresoPorTipoTests(TestCase):
    def setUp(self):
        self.cliente = User.objects.create_user("cliente1", "c@ejemplo.com", CLAVE)
        self.cliente.groups.add(Group.objects.get(name="Cliente"))
        self.tienda = crear_tienda()
        self.url = reverse("login")

    def entrar(self, usuario, tipo, clave=CLAVE):
        return self.client.post(self.url, {"username": usuario, "password": clave, "tipo": tipo})

    def sesion(self):
        return self.client.session.get("_auth_user_id")

    def test_la_pagina_tiene_el_nuevo_diseno(self):
        respuesta = self.client.get(self.url)
        for texto in ("Soy cliente", "Soy tienda", "Nombre de usuario", "Contraseña", 'id="ver-clave"',
                      "¿Olvidaste tu contraseña?", "Entrar a mi tienda", "Regístrala aquí",
                      "Productos tecnológicos de las tiendas de", "ingreso__pila"):
            self.assertContains(respuesta, texto)
        self.assertContains(respuesta, 'id="tipo-cliente" checked')

    def test_el_menu_del_login_es_simple(self):
        respuesta = self.client.get(self.url)
        self.assertNotContains(respuesta, 'id="buscar-menu"')
        self.assertNotContains(respuesta, f'href="{self.url}"')  # no hay enlace a sí mismo
        for nombre in ("inicio", "catalogo:catalogo", "registro", "tiendas:registro"):
            self.assertContains(respuesta, f'href="{reverse(nombre)}"')

    def test_si_viene_de_una_pagina_de_tienda_marca_soy_tienda(self):
        respuesta = self.client.get(self.url, {"next": reverse("inventario:ventas")})
        self.assertContains(respuesta, 'id="tipo-tienda" checked')

    def test_cada_uno_entra_con_su_tipo(self):
        self.assertRedirects(self.entrar("tienda1", "tienda"), reverse("catalogo:mis_productos"), fetch_redirect_response=False)
        self.assertEqual(int(self.sesion()), self.tienda.usuario.pk)
        self.client.logout()
        self.entrar("cliente1", "cliente")
        self.assertEqual(int(self.sesion()), self.cliente.pk)

    def test_tienda_que_elige_soy_cliente_no_entra(self):
        respuesta = self.entrar("tienda1", "cliente")
        self.assertContains(respuesta, "Esta cuenta es de una tienda. Elige «Soy tienda» para entrar.")
        self.assertIsNone(self.sesion())

    def test_cliente_que_elige_soy_tienda_no_entra(self):
        respuesta = self.entrar("cliente1", "tienda")
        self.assertContains(respuesta, "Esta cuenta es de cliente. Elige «Soy cliente» para entrar.")
        self.assertContains(respuesta, 'id="tipo-tienda" checked')  # se mantiene lo que eligió
        self.assertIsNone(self.sesion())

    def test_con_clave_incorrecta_no_revela_el_tipo(self):
        respuesta = self.entrar("tienda1", "cliente", clave="otra-clave")
        self.assertContains(respuesta, "Usuario o contraseña incorrectos")
        self.assertNotContains(respuesta, "Esta cuenta es de")

    def test_el_administrador_entra_con_cualquiera(self):
        User.objects.create_superuser("admin", "a@ejemplo.com", CLAVE)
        self.entrar("admin", "tienda")
        self.assertIsNotNone(self.sesion())


class LogoYCerrarSesionTests(TestCase):
    def test_inicio_tiene_el_logo_animado(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, 'class="logo-portada"')
        self.assertContains(respuesta, 'NEXALYS <tspan fill="#19C3E6">TEC.</tspan>')
        self.assertContains(respuesta, "Lilita+One")

    def test_cerrar_sesion_con_el_estilo_de_la_marca(self):
        self.client.force_login(crear_tienda().usuario)
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, "modal-content modal-marca")
        self.assertContains(respuesta, "Cancelar")
        self.assertNotContains(respuesta, "🚪</div>")
        self.assertNotContains(respuesta, 'class="btn btn-danger px-4">Sí, cerrar sesión')
