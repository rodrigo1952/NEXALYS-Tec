"""
Menú de la cuenta (desplegable), panel de la tienda y Mi cuenta para todos los roles.
"""

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .tests import crear_tienda

CLAVE = "ClaveSegura#2026"


class MenuDeLaCuentaTests(TestCase):
    def setUp(self):
        self.tienda = crear_tienda()
        self.client.force_login(self.tienda.usuario)

    def test_desplegable_de_la_tienda(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, 'class="dropdown-menu dropdown-menu-end menu-cuenta shadow"')
        for nombre in ("tiendas:panel", "mi_cuenta", "ayuda", "privacidad"):
            self.assertContains(respuesta, f'href="{reverse(nombre)}"')
        self.assertContains(respuesta, "ti•••••@ejemplo.com")  # correo parcialmente oculto
        self.assertNotContains(respuesta, f'href="{reverse("tiendas:panel")}">Mi tienda</a>')  # ya no está en la fila de secciones

    def test_cerrar_sesion_pide_confirmacion(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, 'data-bs-target="#modal-cerrar-sesion"')
        self.assertContains(respuesta, "¿Cerrar sesión?")
        self.assertContains(respuesta, "Sí, cerrar sesión")

    def test_el_cliente_no_ve_mi_tienda(self):
        cliente = User.objects.create_user("cliente1", "c@ejemplo.com", CLAVE)
        cliente.groups.add(Group.objects.get(name="Cliente"))
        self.client.force_login(cliente)
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, f'href="{reverse("mi_cuenta")}"')
        self.assertNotContains(respuesta, f'href="{reverse("tiendas:panel")}"')

    def test_visitante_ve_iniciar_sesion(self):
        self.client.logout()
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, "Iniciar sesión")
        self.assertNotContains(respuesta, "modal-cerrar-sesion")

    def test_ayuda_y_privacidad(self):
        self.assertContains(self.client.get(reverse("ayuda")), "soporte@nexalys.pe")
        self.assertContains(self.client.get(reverse("ayuda")), "¿Cómo registro una venta?")
        self.assertContains(self.client.get(reverse("privacidad")), "29733")


class PanelYMiCuentaTests(TestCase):
    def setUp(self):
        self.tienda = crear_tienda()
        self.client.force_login(self.tienda.usuario)

    def test_ver_mi_tienda_publica_junto_al_nombre(self):
        respuesta = self.client.get(reverse("tiendas:panel"))
        html = respuesta.content.decode()
        self.assertIn('class="btn btn-tienda-publica"', html)
        self.assertLess(html.index(self.tienda.nombre), html.index("Ver mi tienda pública"))
        self.assertLess(html.index("Ver mi tienda pública"), html.index("Datos de la tienda"))
        # Los datos y botones de la cuenta ya no están en el panel: están en Mi cuenta.
        self.assertNotContains(respuesta, "Datos de la cuenta")
        self.assertNotContains(respuesta, "Editar datos de mi cuenta")

    def test_sin_logo_muestra_la_inicial(self):
        self.assertContains(self.client.get(reverse("tiendas:panel")), "logo-panel--inicial")

    def test_mi_cuenta_tambien_para_la_tienda(self):
        respuesta = self.client.get(reverse("mi_cuenta"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "logo-panel--inicial")
        for nombre in ("editar_datos", "password_change"):
            self.assertContains(respuesta, f'href="{reverse(nombre)}"')


class ContrasenaParaDatosDeLaTiendaTests(TestCase):
    def setUp(self):
        self.tienda = crear_tienda()
        self.client.force_login(self.tienda.usuario)
        self.url = reverse("tiendas:editar")

    def datos(self, **cambios):
        datos = {"datos-nombre": "Tienda Uno", "datos-direccion": "Jr. Lima 100",
                 "datos-whatsapp": "911111111", "datos-descripcion": ""}
        datos.update(cambios)
        return datos

    def test_cambiar_whatsapp_pide_contrasena(self):
        respuesta = self.client.post(self.url, self.datos(**{"datos-whatsapp": "933333333"}))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("clave_actual", respuesta.context["form"].errors)
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.whatsapp, "911111111")
        respuesta = self.client.post(self.url, self.datos(**{"datos-whatsapp": "933333333", "datos-clave_actual": CLAVE}))
        self.assertRedirects(respuesta, reverse("tiendas:panel"))

    def test_descripcion_no_pide_contrasena(self):
        respuesta = self.client.post(self.url, self.datos(**{"datos-descripcion": "Venta de laptops"}))
        self.assertRedirects(respuesta, reverse("tiendas:panel"))
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.descripcion, "Venta de laptops")

    def test_whatsapp_con_espacios_igual_no_cuenta_como_cambio(self):
        respuesta = self.client.post(self.url, self.datos(**{"datos-whatsapp": "+51 911 111 111"}))
        self.assertRedirects(respuesta, reverse("tiendas:panel"))
