"""Mis productos: tabla blanca con miniatura de la foto, estados con íconos y encabezado limpio."""

import shutil
import tempfile

from django.contrib.staticfiles import finders
from django.test import override_settings
from django.urls import reverse

from .test_fotos import foto
from .tests import BaseCatalogo

CARPETA_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=CARPETA_MEDIA)
class TablaMisProductosTests(BaseCatalogo):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.client.force_login(self.tienda.usuario)

    def test_miniatura_de_la_foto_o_icono_si_no_tiene(self):
        con_foto = self.crear_producto(nombre="Con foto", imagen=foto("principal.png"))
        self.crear_producto(nombre="Sin foto")
        respuesta = self.client.get(reverse("catalogo:mis_productos"))
        # Usa la miniatura chica (160 px) y no la foto de 1200 px.
        icono = "/media/miniaturas/icono/" + con_foto.imagen.name.rsplit(".", 1)[0] + ".webp"
        self.assertContains(respuesta, f'<img src="{icono}" alt="" class="miniatura-tabla" width="48" height="48" loading="lazy"')
        self.assertContains(respuesta, 'class="miniatura-tabla miniatura-tabla--vacia" title="Sin foto"', count=1)

    def test_estados_y_botones_con_iconos(self):
        self.crear_producto(nombre="Destacado", destacado=True)
        self.crear_producto(nombre="Oculto", activo=False, stock=0)
        respuesta = self.client.get(reverse("catalogo:mis_productos"))
        for parte in ('<i class="bi bi-eye" aria-hidden="true"></i> Publicado', '<i class="bi bi-eye-slash" aria-hidden="true"></i> Oculto',
                      '<i class="bi bi-star-fill" aria-hidden="true"></i> Destacado', '<i class="bi bi-x-circle" aria-hidden="true"></i> Agotado',
                      '<i class="bi bi-pencil" aria-hidden="true"></i> Editar', 'class="table table-hover align-middle mb-0 tabla-productos"'):
            self.assertContains(respuesta, parte)
        self.assertNotContains(respuesta, "⭐ Destacado")

    def test_todas_las_tablas_son_blancas_con_celeste_al_pasar_el_mouse(self):
        with open(finders.find("css/marca.css"), encoding="utf-8") as archivo:
            css = archivo.read()
        self.assertIn(".table { --bs-table-bg: var(--nx-blanco); --bs-table-hover-bg: rgba(var(--nx-acento-rgb), .08);", css)
