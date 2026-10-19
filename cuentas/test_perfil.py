"""
Pruebas de la gestión de cuenta (Etapa 1 del perfil del cliente):
editar datos, cambiar y recuperar contraseña, y eliminar la cuenta.
"""

import re

from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Marca, Producto
from favoritos.models import Favorito
from tiendas.tests import crear_tienda

CLAVE = "ClaveSegura#2026"


def crear_cliente(usuario="cliente1"):
    user = User.objects.create_user(
        usuario, f"{usuario}@ejemplo.com", CLAVE, first_name="Ana", last_name="Quispe"
    )
    user.groups.add(Group.objects.get(name="Cliente"))
    return user


class EditarDatosTests(TestCase):
    def setUp(self):
        self.cliente = crear_cliente()
        self.client.force_login(self.cliente)
        self.url = reverse("editar_datos")

    def enviar(self, **cambios):
        datos = {"first_name": "Ana", "last_name": "Quispe", "email": "cliente1@ejemplo.com", "clave_actual": ""}
        datos.update(cambios)
        return self.client.post(self.url, datos)

    def test_cambiar_nombre_no_pide_contrasena(self):
        respuesta = self.enviar(first_name="Ana María")
        self.assertRedirects(respuesta, reverse("mi_cuenta"))
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.first_name, "Ana María")

    def test_cambiar_correo_sin_contrasena_no_se_permite(self):
        respuesta = self.enviar(email="nuevo@ejemplo.com")
        self.assertEqual(respuesta.status_code, 200)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.email, "cliente1@ejemplo.com")

    def test_cambiar_correo_con_contrasena(self):
        respuesta = self.enviar(email="Nuevo@Ejemplo.com", clave_actual=CLAVE)
        self.assertRedirects(respuesta, reverse("mi_cuenta"))
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.email, "nuevo@ejemplo.com")

    def test_correo_de_otro_usuario_no_se_permite(self):
        crear_cliente("cliente2")
        self.enviar(email="cliente2@ejemplo.com", clave_actual=CLAVE)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.email, "cliente1@ejemplo.com")

    def test_nombre_obligatorio(self):
        respuesta = self.enviar(first_name="")
        self.assertEqual(respuesta.status_code, 200)

    def test_requiere_iniciar_sesion(self):
        self.client.logout()
        respuesta = self.client.get(self.url)
        self.assertRedirects(respuesta, f"{reverse('login')}?next={self.url}")


class ContrasenaTests(TestCase):
    def setUp(self):
        self.cliente = crear_cliente()

    def test_cambiar_contrasena(self):
        self.client.force_login(self.cliente)
        respuesta = self.client.post(reverse("password_change"), {
            "old_password": CLAVE,
            "new_password1": "OtraClave#2027",
            "new_password2": "OtraClave#2027",
        })
        self.assertRedirects(respuesta, reverse("password_change_done"))
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.check_password("OtraClave#2027"))

    def test_login_tiene_enlace_para_recuperar(self):
        self.assertContains(self.client.get(reverse("login")), reverse("password_reset"))

    def test_recuperar_contrasena_por_correo(self):
        respuesta = self.client.post(reverse("password_reset"), {"email": "cliente1@ejemplo.com"})
        self.assertRedirects(respuesta, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["cliente1@ejemplo.com"])

        enlace = re.search(r"https?://[^/\s]+(/cuentas/reset/\S+/)", mail.outbox[0].body).group(1)
        # Django cambia el token del enlace por "set-password" y redirige.
        respuesta = self.client.get(enlace, follow=True)
        self.assertTrue(respuesta.context["validlink"])
        url_formulario = respuesta.redirect_chain[-1][0]

        respuesta = self.client.post(url_formulario, {
            "new_password1": "NuevaClave#2027",
            "new_password2": "NuevaClave#2027",
        })
        self.assertRedirects(respuesta, reverse("password_reset_complete"))
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.check_password("NuevaClave#2027"))

    def test_correo_desconocido_no_envia_nada(self):
        self.client.post(reverse("password_reset"), {"email": "nadie@ejemplo.com"})
        self.assertEqual(len(mail.outbox), 0)


class EliminarCuentaTests(TestCase):
    def setUp(self):
        self.cliente = crear_cliente()
        self.url = reverse("eliminar_cuenta")

    def test_contrasena_incorrecta_no_elimina(self):
        self.client.force_login(self.cliente)
        self.client.post(self.url, {"clave": "incorrecta", "confirmar": "on"})
        self.assertTrue(User.objects.filter(pk=self.cliente.pk).exists())

    def test_sin_confirmar_no_elimina(self):
        self.client.force_login(self.cliente)
        self.client.post(self.url, {"clave": CLAVE})
        self.assertTrue(User.objects.filter(pk=self.cliente.pk).exists())

    def test_elimina_la_cuenta_y_sus_favoritos(self):
        tienda = crear_tienda()
        categoria, _ = Categoria.objects.get_or_create(nombre="Celulares")
        marca, _ = Marca.objects.get_or_create(nombre="Samsung")
        producto = Producto.objects.create(
            tienda=tienda, categoria=categoria, marca=marca, nombre="Galaxy", precio="500.00", stock=2
        )
        Favorito.guardar(self.cliente, producto)

        self.client.force_login(self.cliente)
        respuesta = self.client.post(self.url, {"clave": CLAVE, "confirmar": "on"})
        self.assertRedirects(respuesta, reverse("inicio"))
        self.assertFalse(User.objects.filter(pk=self.cliente.pk).exists())
        self.assertFalse(Favorito.objects.exists())
        self.assertTrue(Producto.objects.filter(pk=producto.pk).exists())  # el producto de la tienda sigue
        self.assertNotIn("_auth_user_id", self.client.session)  # se cerró la sesión

    def test_una_tienda_no_puede_eliminar_su_cuenta_aqui(self):
        tienda = crear_tienda()
        self.client.force_login(tienda.usuario)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_mi_cuenta_muestra_la_opcion_solo_al_cliente(self):
        self.client.force_login(self.cliente)
        self.assertContains(self.client.get(reverse("mi_cuenta")), self.url)
        self.client.force_login(crear_tienda().usuario)
        self.assertNotContains(self.client.get(reverse("mi_cuenta")), self.url)
