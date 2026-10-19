"""
Prueba del registro simultáneo con los mismos datos.

Se simula así: el formulario de la persona A ya pasó la validación ("el usuario
no existe"), y antes de que se guarde, la persona B termina de registrarse con
el mismo usuario. Antes de la corrección esto daba error 500.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from tiendas.forms import RegistroTiendaForm
from tiendas.models import Tienda
from tiendas.tests import DATOS_VALIDOS

from .concurrencia import MENSAJE_DUPLICADO, validar_y_guardar
from .forms import RegistroForm

DATOS_CLIENTE = {
    "username": "ana",
    "first_name": "Ana",
    "last_name": "Quispe",
    "email": "ana@ejemplo.com",
    "password1": "ClaveSegura#2026",
    "password2": "ClaveSegura#2026",
}


class RegistroSimultaneoTests(TestCase):
    def test_registro_cliente_duplicado_simultaneo(self):
        form_a = RegistroForm(DATOS_CLIENTE)
        self.assertTrue(form_a.is_valid())  # A valida: "ana" está libre

        User.objects.create_user("ana", "otra@ejemplo.com", "ClaveSegura#2026")  # B gana la carrera

        # validar_y_guardar reutiliza la validación ya hecha y guarda: la base de datos rechaza el duplicado.
        resultado = validar_y_guardar(form_a)
        self.assertIsNone(resultado)
        self.assertIn(MENSAJE_DUPLICADO, form_a.non_field_errors())
        self.assertEqual(User.objects.filter(username="ana").count(), 1)

    def test_registro_tienda_duplicado_simultaneo(self):
        form_a = RegistroTiendaForm(DATOS_VALIDOS)
        self.assertTrue(form_a.is_valid())

        # B registra antes una tienda con el mismo WhatsApp.
        otro = User.objects.create_user("otra", "otra@ejemplo.com", "ClaveSegura#2026")
        Tienda.objects.create(usuario=otro, nombre="Otra tienda", direccion="Jr. Lima 1", whatsapp="987654321")

        self.assertIsNone(validar_y_guardar(form_a))
        self.assertIn(MENSAJE_DUPLICADO, form_a.non_field_errors())
        # No quedó un usuario huérfano sin tienda: se deshizo todo el registro de A.
        self.assertFalse(User.objects.filter(username=DATOS_VALIDOS["username"]).exists())

    def test_registro_normal_sigue_funcionando(self):
        usuario = validar_y_guardar(RegistroForm(DATOS_CLIENTE))
        self.assertEqual(usuario.username, "ana")
