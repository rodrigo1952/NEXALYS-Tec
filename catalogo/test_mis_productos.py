"""Etapa 1 (inventario): cantidades por categoría y marca en "Mis productos" y avatar del menú."""

import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from .models import Categoria, Marca
from .tests import BaseCatalogo

CARPETA_MEDIA = tempfile.mkdtemp()


class ConteosMisProductosTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.laptops, _ = Categoria.objects.get_or_create(nombre="Laptops")
        self.hp, _ = Marca.objects.get_or_create(nombre="HP")
        self.crear_producto(nombre="Galaxy A15")
        self.crear_producto(nombre="Galaxy A25")
        self.crear_producto(nombre="HP OmniBook", categoria=self.laptops, marca=self.hp)
        self.crear_producto(tienda=self.otra_tienda, nombre="De otra tienda")
        self.client.force_login(self.tienda.usuario)
        self.url = reverse("catalogo:mis_productos")

    def nombres(self, respuesta):
        return sorted(p.nombre for p in respuesta.context["pagina"])

    def test_muestra_cantidad_por_categoria_solo_de_mi_tienda(self):
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, "Todas (3)")
        self.assertContains(respuesta, "Celulares (2)")
        self.assertContains(respuesta, "Laptops (1)")

    def test_filtrar_por_categoria(self):
        respuesta = self.client.get(self.url, {"categoria": self.laptops.pk})
        self.assertEqual(self.nombres(respuesta), ["HP OmniBook"])

    def test_desplegable_de_marcas_con_cantidad(self):
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, "Samsung (2)")
        self.assertContains(respuesta, "HP (1)")
        respuesta = self.client.get(self.url, {"marca": self.marca.pk})
        self.assertEqual(self.nombres(respuesta), ["Galaxy A15", "Galaxy A25"])

    def test_las_marcas_se_cuentan_dentro_de_la_categoria_elegida(self):
        respuesta = self.client.get(self.url, {"categoria": self.laptops.pk})
        self.assertContains(respuesta, "HP (1)")
        self.assertNotContains(respuesta, "Samsung (2)")

    def test_filtro_invalido_no_rompe_la_pagina(self):
        self.assertEqual(self.client.get(self.url, {"categoria": "abc", "marca": "x"}).status_code, 200)


@override_settings(MEDIA_ROOT=CARPETA_MEDIA)
class AvatarMenuTests(BaseCatalogo):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def test_tienda_con_logo_lo_ve_en_el_menu(self):
        archivo = io.BytesIO()
        Image.new("RGB", (20, 20), "red").save(archivo, "PNG")
        self.tienda.logo = SimpleUploadedFile("logo.png", archivo.getvalue(), content_type="image/png")
        self.tienda.save()
        self.client.force_login(self.tienda.usuario)
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, f'<span class="avatar-menu" aria-hidden="true"><img src="{self.tienda.logo.url}"')
        self.assertNotContains(respuesta, "👤")

    def test_sin_logo_se_ve_la_inicial(self):
        self.client.force_login(self.tienda.usuario)
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, '<span class="avatar-menu" aria-hidden="true">T</span>')
