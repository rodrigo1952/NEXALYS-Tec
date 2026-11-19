"""Escaneos del QR de cada tienda: se cuentan al entrar con «?desde=qr» y se ven en «Mi código QR»."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from administracion.test_consola import crear_admin

from . import qr
from .models import EscaneoQR, Tienda
from .tests import crear_tienda


class ContarEscaneosTests(TestCase):
    def setUp(self):
        self.tienda = crear_tienda()
        self.pagina = reverse("tiendas:perfil", args=[self.tienda.pk])

    def test_cuenta_una_vez_por_visita_y_limpia_la_direccion(self):
        self.assertRedirects(self.client.get(f"{self.pagina}?desde=qr"), self.pagina)
        self.client.get(f"{self.pagina}?desde=qr")  # el mismo celular vuelve a escanear en la misma visita
        self.assertEqual(self.tienda.escaneos_qr.count(), 1)
        self.client_class().get(f"{self.pagina}?desde=qr")  # otro celular
        self.assertEqual(self.tienda.escaneos_qr.count(), 2)

    def test_cada_tienda_cuenta_aparte(self):
        otra = crear_tienda(usuario="tienda2", nombre="Tienda Dos", whatsapp="922222222")
        self.client.get(f"{self.pagina}?desde=qr")
        self.client.get(f"{reverse('tiendas:perfil', args=[otra.pk])}?desde=qr")
        self.assertEqual(self.tienda.escaneos_qr.count(), 1)
        self.assertEqual(otra.escaneos_qr.count(), 1)

    def test_la_pagina_normal_y_los_enlaces_compartidos_no_cuentan(self):
        self.client.get(self.pagina)
        self.client.get(f"{self.pagina}?desde=whatsapp")
        self.assertEqual(EscaneoQR.objects.count(), 0)

    def test_no_cuenta_la_propia_tienda_ni_el_administrador(self):
        self.client.force_login(self.tienda.usuario)
        self.client.get(f"{self.pagina}?desde=qr")
        self.client.force_login(crear_admin())
        self.client.get(f"{self.pagina}?desde=qr")
        self.assertEqual(EscaneoQR.objects.count(), 0)

    def test_tienda_no_activa(self):
        self.tienda.estado = Tienda.Estado.SUSPENDIDA
        self.tienda.save()
        self.assertEqual(self.client.get(f"{self.pagina}?desde=qr").status_code, 404)
        self.assertEqual(EscaneoQR.objects.count(), 0)


class ResumenEscaneosTests(TestCase):
    def setUp(self):
        self.tienda = crear_tienda()
        self.client.force_login(self.tienda.usuario)

    def crear(self, cuando):
        escaneo = EscaneoQR.objects.create(tienda=self.tienda)
        EscaneoQR.objects.filter(pk=escaneo.pk).update(fecha=cuando)

    def test_numeros(self):
        ahora = timezone.now()
        inicio_mes = timezone.localtime(ahora).replace(day=1, hour=12, minute=0)
        for _ in range(3):
            self.crear(ahora)
        self.crear(inicio_mes - timedelta(days=5))  # el mes pasado
        datos = qr.resumen_escaneos(self.tienda)
        self.assertEqual((datos["este_mes"], datos["mes_anterior"], datos["total"], datos["diferencia"]), (3, 1, 4, 2))
        mes_pasado = qr.MESES[(inicio_mes - timedelta(days=5)).month - 1]
        self.assertEqual(datos["comparacion"], f"2 más que en {mes_pasado}")
        self.assertTrue(datos["ultimo"].startswith("Hoy, "))

    def test_sin_escaneos(self):
        respuesta = self.client.get(reverse("tiendas:qr"))
        self.assertContains(respuesta, '<p class="escaneos-qr__numero escaneos-qr__numero--texto">Todavía no</p>')
        self.assertContains(respuesta, "Escaneos este mes</p>")

    def test_se_ven_en_mi_codigo_qr(self):
        self.crear(timezone.now())
        self.crear(timezone.now())
        respuesta = self.client.get(reverse("tiendas:qr"))
        self.assertContains(respuesta, 'aria-label="Escaneos de tu código QR"')
        self.assertContains(respuesta, '<p class="escaneos-qr__numero">2</p>')
        self.assertContains(respuesta, "Cada celular cuenta una vez por visita")
