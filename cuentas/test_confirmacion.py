"""Los clientes también confirman su correo antes de poder iniciar sesión."""

import re
from datetime import timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from administracion import limpieza

from .models import CorreoPendiente

CLAVE = "ClaveSegura#2026"
DATOS = {
    "username": "cliente1", "first_name": "Ana", "last_name": "Quispe",
    "email": "ana@ejemplo.com", "password1": CLAVE, "password2": CLAVE,
}


class ConfirmacionCorreoClienteTests(TestCase):
    def registrar(self):
        return self.client.post(reverse("registro"), DATOS)

    def enlace(self):
        return re.search(r"http://testserver(/\S+)", mail.outbox[-1].body).group(1)

    def test_registro_envia_correo_y_no_inicia_sesion(self):
        respuesta = self.registrar()
        self.assertRedirects(respuesta, reverse("confirmacion_pendiente"))
        usuario = User.objects.get(username="cliente1")
        self.assertFalse(usuario.is_active)
        self.assertTrue(CorreoPendiente.objects.filter(usuario=usuario).exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ana@ejemplo.com"])
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(self.client.get(reverse("confirmacion_pendiente")), "ana@ejemplo.com")

    def test_sin_confirmar_no_puede_entrar_y_se_le_explica(self):
        self.registrar()
        respuesta = self.client.post(reverse("login"), {"username": "cliente1", "password": CLAVE})
        self.assertContains(respuesta, "Primero confirma tu correo")
        self.assertNotContains(respuesta, "desactivada")

    def test_el_enlace_activa_la_cuenta_e_inicia_sesion(self):
        self.registrar()
        respuesta = self.client.get(self.enlace(), follow=True)
        usuario = User.objects.get(username="cliente1")
        self.assertTrue(usuario.is_active)
        self.assertFalse(CorreoPendiente.objects.exists())
        self.assertEqual(int(self.client.session["_auth_user_id"]), usuario.pk)
        self.assertContains(respuesta, "Correo confirmado")

    def test_enlace_falso_muestra_aviso_y_opcion_de_reenviar(self):
        respuesta = self.client.get(reverse("confirmar_correo", args=["falso"]))
        self.assertEqual(respuesta.status_code, 400)
        self.assertContains(respuesta, "no es válido o ya venció", status_code=400)
        self.assertContains(respuesta, "Reenviar enlace", status_code=400)

    def test_reenviar_enlace(self):
        self.registrar()
        respuesta = self.client.post(reverse("reenviar_confirmacion"), {"email": "ANA@ejemplo.com"}, follow=True)
        self.assertEqual(len(mail.outbox), 2)
        self.assertContains(respuesta, "te enviamos un enlace nuevo")

    def test_reenviar_no_revela_si_el_correo_existe(self):
        respuesta = self.client.post(reverse("reenviar_confirmacion"), {"email": "nadie@ejemplo.com"}, follow=True)
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(respuesta, "Si ese correo corresponde a una cuenta sin confirmar")

    def test_los_clientes_existentes_no_tienen_que_confirmar(self):
        User.objects.create_user("antiguo", "a@ejemplo.com", CLAVE)
        self.assertTrue(self.client.login(username="antiguo", password=CLAVE))

    def test_sin_confirmar_en_7_dias_se_elimina(self):
        self.registrar()
        CorreoPendiente.objects.update(creado=timezone.now() - timedelta(days=7, minutes=1))
        self.assertEqual(limpieza.ejecutar(), (0, 1))
        self.assertFalse(User.objects.filter(username="cliente1").exists())

    def test_antes_de_7_dias_no_se_elimina(self):
        self.registrar()
        CorreoPendiente.objects.update(creado=timezone.now() - timedelta(days=6))
        limpieza.ejecutar()
        self.assertTrue(User.objects.filter(username="cliente1").exists())

    def test_el_admin_ve_sin_confirmar_y_puede_activarla(self):
        self.registrar()
        admin = User.objects.create_superuser("admin", "admin@ejemplo.com", CLAVE)
        self.client.force_login(admin)
        self.assertContains(self.client.get(reverse("administracion:usuarios")), "Sin confirmar correo")
        usuario = User.objects.get(username="cliente1")
        self.client.post(reverse("administracion:usuario_reactivar", args=[usuario.pk]))
        usuario.refresh_from_db()
        self.assertTrue(usuario.is_active)
        self.assertFalse(CorreoPendiente.objects.exists())
