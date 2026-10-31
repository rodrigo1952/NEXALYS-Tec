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
        for nombre in ("mi_cuenta", "ayuda", "privacidad"):
            self.assertContains(respuesta, f'href="{reverse(nombre)}"')
        # «Mi tienda» lleva a la página pública de la tienda (los datos están en Mi cuenta).
        publica = reverse("tiendas:perfil", args=[self.tienda.pk])
        self.assertContains(respuesta, f'<a class="dropdown-item" href="{publica}"><span aria-hidden="true">🏪</span> Mi tienda</a>', html=True)
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

    def test_tienda_pendiente_va_a_datos_de_mi_tienda(self):
        self.tienda.estado = "pendiente"
        self.tienda.save()
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, f'<a class="dropdown-item" href="{reverse("tiendas:panel")}"><span aria-hidden="true">🏪</span> Mi tienda</a>', html=True)

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

    def test_ya_no_hay_boton_ver_mi_tienda_publica(self):
        # Se llega desde «Mi tienda» en el menú de la cuenta; aquí ya no se repite.
        respuesta = self.client.get(reverse("tiendas:panel"))
        self.assertNotContains(respuesta, "Ver mi tienda pública")
        self.assertContains(respuesta, "Editar datos, logo y horario")
        # Los datos y botones de la cuenta ya no están en el panel: están en Mi cuenta.
        self.assertNotContains(respuesta, "Datos de la cuenta")
        self.assertNotContains(respuesta, "Editar datos de mi cuenta")

    def test_sin_logo_muestra_la_inicial(self):
        self.assertContains(self.client.get(reverse("tiendas:panel")), "logo-panel--inicial")

    def test_mi_cuenta_tambien_para_la_tienda(self):
        respuesta = self.client.get(reverse("mi_cuenta"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'id="cambiar-logo"')  # el círculo del logo se puede tocar para cambiarlo
        for nombre in ("editar_datos", "password_change", "tiendas:panel"):
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
