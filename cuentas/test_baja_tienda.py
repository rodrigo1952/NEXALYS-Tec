"""Nov 2026: la tienda pide su baja (derecho de cancelación); llega a la consola y el administrador la elimina."""

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from cuentas.models import SolicitudDerecho
from tiendas.models import Tienda
from tiendas.tests import crear_tienda

from .test_privacidad import crear_cliente

CLAVE = "ClaveSegura#2026"


class SolicitarBajaTests(TestCase):
    def setUp(self):
        self.tienda = crear_tienda()
        self.client.force_login(self.tienda.usuario)
        self.url = reverse("baja_tienda")

    def test_boton_en_mi_perfil(self):
        self.assertContains(self.client.get(reverse("mi_cuenta")), f'href="{self.url}"')

    def test_pide_contrasena_y_confirmacion(self):
        respuesta = self.client.post(self.url, {"clave": "otra", "confirmar": "on"})
        self.assertContains(respuesta, "La contraseña no es correcta.")
        self.client.post(self.url, {"clave": CLAVE})
        self.assertFalse(SolicitudDerecho.objects.exists())

    def test_envia_la_solicitud_y_la_tienda_sigue_funcionando(self):
        respuesta = self.client.post(self.url, {"clave": CLAVE, "confirmar": "on", "motivo": "Cierro el local"})
        self.assertContains(respuesta, "Recibimos tu solicitud")
        solicitud = SolicitudDerecho.objects.get()
        self.assertEqual((solicitud.tipo, solicitud.usuario, solicitud.correo),
                         ("cancelacion", self.tienda.usuario, "tienda1@ejemplo.com"))
        self.assertIn("«Tienda Uno»", solicitud.detalle)
        self.assertIn("Cierro el local", solicitud.detalle)
        self.assertEqual(len(mail.outbox), 1)  # constancia
        self.assertTrue(Tienda.objects.filter(pk=self.tienda.pk).exists())
        # Una segunda vez solo muestra que ya la envió.
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, "Ya enviaste tu solicitud")
        self.client.post(self.url, {"clave": CLAVE, "confirmar": "on"})
        self.assertEqual(SolicitudDerecho.objects.count(), 1)

    def test_un_cliente_no_tiene_esta_pagina(self):
        self.client.force_login(crear_cliente())
        self.assertEqual(self.client.get(self.url).status_code, 403)


class AdministradorAtiendeLaBajaTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", "admin@ejemplo.com", CLAVE)
        self.tienda = crear_tienda()
        self.client.force_login(self.tienda.usuario)
        self.client.post(reverse("baja_tienda"), {"clave": CLAVE, "confirmar": "on"})
        self.solicitud = SolicitudDerecho.objects.get()
        self.client.force_login(self.admin)

    def test_desde_la_solicitud_se_elimina_y_vuelve_para_responder(self):
        detalle = reverse("administracion:solicitud_detalle", args=[self.solicitud.pk])
        eliminar = reverse("administracion:usuario_eliminar", args=[self.tienda.usuario.pk])
        respuesta = self.client.get(detalle)
        self.assertContains(respuesta, f'href="{eliminar}"')
        self.assertContains(respuesta, "Eliminar la cuenta y la tienda")
        self.assertContains(self.client.get(eliminar), "Pidió su baja")
        respuesta = self.client.post(eliminar, {"confirmar": "on", "motivo": "La tienda pidió su baja"})
        self.assertRedirects(respuesta, detalle)
        self.assertFalse(Tienda.objects.exists())
        self.assertContains(self.client.get(detalle), "la cuenta ya fue eliminada")
