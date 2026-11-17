"""
Mensajes de WhatsApp para la tienda (nov 2026, catalogo/whatsapp.py): saludo según la hora de Perú,
«Soy <nombre>.» si inició sesión, producto en negrita con su precio y el enlace al final.
"""

from datetime import datetime
from decimal import Decimal
from unittest import mock
from urllib.parse import unquote
from zoneinfo import ZoneInfo

from django.contrib.auth.models import AnonymousUser, Group, User
from django.test import override_settings
from django.urls import reverse

from catalogo import whatsapp

from .tests import BaseCatalogo

LIMA = ZoneInfo("America/Lima")
SITIO = "https://nexalys.pe"


def a_las(hora, minuto=0):
    return mock.patch("catalogo.whatsapp.timezone.now", return_value=datetime(2026, 11, 16, hora, minuto, tzinfo=LIMA))


@override_settings(SITIO_URL=SITIO)
class MensajesTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.producto = self.crear_producto(nombre="Samsung Galaxy A26 5G", precio=Decimal("1199"))
        self.cliente = User.objects.create_user("david", "d@ejemplo.com", "ClaveSegura#2026", first_name="David Antonio")
        self.cliente.groups.add(Group.objects.get(name="Cliente"))

    def test_saludo_segun_la_hora(self):
        for hora, esperado in ((5, "Buenos días"), (11, "Buenos días"), (12, "Buenas tardes"),
                               (18, "Buenas tardes"), (19, "Buenas noches"), (2, "Buenas noches")):
            with a_las(hora):
                self.assertEqual(whatsapp.saludo(), esperado)

    def test_mensaje_del_producto(self):
        with a_las(15):
            mensaje = self.producto.mensaje_whatsapp()
        self.assertEqual(mensaje, (
            f"Buenas tardes, {self.tienda.nombre}. Vi este producto en NEXALYS Tec:\n\n"
            "*Samsung Galaxy A26 5G*\nPrecio: S/ 1,199.00\n\n"
            "¿Sigue disponible? ¿Cómo puedo comprarlo?\n\n"
            f"{SITIO}/catalogo/producto/{self.producto.pk}/"
        ))

    def test_con_sesion_dice_solo_el_primer_nombre(self):
        with a_las(9):
            mensaje = self.producto.mensaje_whatsapp(self.cliente)
        self.assertTrue(mensaje.startswith(f"Buenos días, {self.tienda.nombre}. Soy David. Vi este producto"))
        self.assertNotIn("d@ejemplo.com", mensaje)
        self.assertNotIn("david", mensaje)  # nunca el nombre de usuario
        # Sin nombre o sin sesión: no se presenta.
        sin_nombre = User.objects.create_user("x_prueba", "x@ejemplo.com", "ClaveSegura#2026")
        self.assertNotIn("Soy", self.producto.mensaje_whatsapp(sin_nombre))
        self.assertNotIn("Soy", self.producto.mensaje_whatsapp(AnonymousUser()))

    def test_los_asteriscos_del_nombre_no_rompen_la_negrita(self):
        self.producto.nombre = "Mouse *gamer*"
        self.assertIn("*Mouse gamer*", self.producto.mensaje_whatsapp())

    def test_mensaje_de_la_tienda(self):
        with a_las(20):
            mensaje = whatsapp.mensaje_tienda(self.tienda, self.cliente)
        self.assertEqual(mensaje, (
            f"Buenas noches, {self.tienda.nombre}. Soy David. Encontré su tienda en NEXALYS Tec y quisiera "
            f"hacerles una consulta.\n\n{SITIO}/tiendas/{self.tienda.pk}/"
        ))

    def test_las_paginas_usan_el_nombre_de_quien_las_ve(self):
        self.client.force_login(self.cliente)
        for url in (reverse("catalogo:detalle", args=[self.producto.pk]), reverse("tiendas:perfil", args=[self.tienda.pk]),
                    reverse("tiendas:cercanas")):
            html = unquote(self.client.get(url).content.decode())
            self.assertIn(f", {self.tienda.nombre}. Soy David.", html, url)
        self.client.logout()
        html = unquote(self.client.get(reverse("tiendas:perfil", args=[self.tienda.pk])).content.decode())
        self.assertIn("Encontré su tienda en NEXALYS Tec", html)
        self.assertNotIn("Soy David", html)

    def test_cambiar_whatsapp_en_favoritos_y_tiendas_cercanas(self):
        self.client.force_login(self.cliente)
        from favoritos.models import Favorito

        Favorito.guardar(self.cliente, self.producto)
        for url in (reverse("favoritos:lista"), reverse("tiendas:cercanas")):
            self.assertContains(self.client.get(url), "data-modo-whatsapp hidden")
