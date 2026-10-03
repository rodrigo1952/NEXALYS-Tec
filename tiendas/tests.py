"""
Pruebas del registro y la verificación de tiendas (CU-01).
Ejecutar con:  python manage.py test
"""

import time
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .models import Tienda
from .verificacion import generar_token, leer_token

DATOS_VALIDOS = {
    "nombre_tienda": "Tecno Quillabamba",
    "direccion": "Av. Principal 123, Quillabamba",
    "whatsapp": "987654321",
    "descripcion": "Celulares y accesorios",
    "username": "tecnoq",
    "email": "tecnoq@ejemplo.com",
    "password1": "ClaveSegura#2026",
    "password2": "ClaveSegura#2026",
}


def crear_tienda(usuario="tienda1", nombre="Tienda Uno", whatsapp="911111111", estado=Tienda.Estado.ACTIVA):
    user = User.objects.create_user(usuario, f"{usuario}@ejemplo.com", "ClaveSegura#2026")
    return Tienda.objects.create(
        usuario=user, nombre=nombre, direccion="Jr. Lima 100", whatsapp=whatsapp, estado=estado
    )


class RegistroTiendaTests(TestCase):
    url = reverse("tiendas:registro")

    def registrar(self, **cambios):
        return self.client.post(self.url, {**DATOS_VALIDOS, **cambios})

    def test_registro_crea_tienda_pendiente_y_envia_correo(self):
        respuesta = self.registrar()
        self.assertRedirects(respuesta, reverse("tiendas:panel"))
        tienda = Tienda.objects.get(nombre="Tecno Quillabamba")
        self.assertEqual(tienda.estado, Tienda.Estado.PENDIENTE)
        self.assertTrue(tienda.usuario.groups.filter(name="Tienda").exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["tecnoq@ejemplo.com"])
        self.assertIn("/tiendas/verificar/", mail.outbox[0].body)

    def test_whatsapp_con_formato_invalido_se_rechaza(self):
        respuesta = self.registrar(whatsapp="12345")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("whatsapp", respuesta.context["form"].errors)
        self.assertFalse(Tienda.objects.exists())

    def test_whatsapp_con_prefijo_y_espacios_se_normaliza(self):
        self.registrar(whatsapp="+51 987 654 321")
        self.assertEqual(Tienda.objects.get().whatsapp, "987654321")

    def test_whatsapp_duplicado_se_rechaza(self):
        crear_tienda(whatsapp="987654321")
        respuesta = self.registrar()
        self.assertIn("whatsapp", respuesta.context["form"].errors)

    def test_nombre_de_tienda_duplicado_sin_importar_mayusculas(self):
        crear_tienda(nombre="TECNO QUILLABAMBA")
        respuesta = self.registrar()
        self.assertIn("nombre_tienda", respuesta.context["form"].errors)

    def test_correo_duplicado_se_rechaza(self):
        User.objects.create_user("otro", "TecnoQ@ejemplo.com", "x")
        respuesta = self.registrar()
        self.assertIn("email", respuesta.context["form"].errors)

    def test_campos_obligatorios_vacios(self):
        respuesta = self.client.post(self.url, {})
        errores = respuesta.context["form"].errors
        for campo in ["nombre_tienda", "direccion", "whatsapp", "username", "email", "password1"]:
            self.assertIn(campo, errores)


class VerificacionCorreoTests(TestCase):
    def setUp(self):
        self.tienda = crear_tienda(estado=Tienda.Estado.PENDIENTE)

    def test_enlace_valido_activa_la_tienda_sin_administrador(self):
        self.client.get(reverse("tiendas:verificar", args=[generar_token(self.tienda)]))
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.estado, Tienda.Estado.ACTIVA)
        self.assertIsNotNone(self.tienda.verificada_en)

    def test_enlace_alterado_es_invalido(self):
        token = generar_token(self.tienda) + "x"
        respuesta = self.client.get(reverse("tiendas:verificar", args=[token]))
        self.assertEqual(respuesta.status_code, 400)
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.estado, Tienda.Estado.PENDIENTE)

    def test_enlace_vencido_es_invalido(self):
        token = generar_token(self.tienda)
        dentro_de_25_horas = time.time() + 25 * 3600
        with mock.patch("django.core.signing.time.time", return_value=dentro_de_25_horas):
            self.assertIsNone(leer_token(token))

    def test_tienda_suspendida_no_se_reactiva_con_el_enlace(self):
        self.tienda.estado = Tienda.Estado.SUSPENDIDA
        self.tienda.save()
        self.client.get(reverse("tiendas:verificar", args=[generar_token(self.tienda)]))
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.estado, Tienda.Estado.SUSPENDIDA)

    def test_reenviar_envia_un_nuevo_correo(self):
        self.client.force_login(self.tienda.usuario)
        self.client.post(reverse("tiendas:reenviar"))
        self.assertEqual(len(mail.outbox), 1)

    def test_tienda_pendiente_no_puede_crear_productos(self):
        self.client.force_login(self.tienda.usuario)
        respuesta = self.client.get(reverse("catalogo:crear"))
        self.assertRedirects(respuesta, reverse("tiendas:panel"))


class PerfilTiendaTests(TestCase):
    def test_perfil_de_tienda_activa_es_publico(self):
        tienda = crear_tienda()
        respuesta = self.client.get(reverse("tiendas:perfil", args=[tienda.pk]))
        self.assertContains(respuesta, tienda.direccion)

    def test_perfil_de_tienda_suspendida_no_existe(self):
        tienda = crear_tienda(estado=Tienda.Estado.SUSPENDIDA)
        respuesta = self.client.get(reverse("tiendas:perfil", args=[tienda.pk]))
        self.assertEqual(respuesta.status_code, 404)
