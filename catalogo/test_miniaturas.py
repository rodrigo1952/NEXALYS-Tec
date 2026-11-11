"""Miniaturas: copias chicas de las fotos para las tarjetas (cargan más rápido) que se borran con la original."""
import os
import shutil
import tempfile
from pathlib import Path

from django.core.files.storage import default_storage
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from favoritos.models import Favorito

from .imagenes import ruta_miniatura, url_miniatura
from .models import FotoProducto
from .test_fotos import foto
from .tests import BaseCatalogo

CARPETA_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=CARPETA_MEDIA)
class MiniaturasTests(BaseCatalogo):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def archivo(self, ruta):
        return Path(CARPETA_MEDIA) / ruta

    def con_foto(self, **datos):
        return self.crear_producto(imagen=foto("principal.png", 1000, 800), **datos)

    def test_crea_la_miniatura_chica_en_webp(self):
        producto = self.con_foto()
        url = url_miniatura(producto.imagen)
        ruta = ruta_miniatura(producto.imagen.name, "tarjeta")
        self.assertEqual(url, f"/media/{ruta}")
        with Image.open(self.archivo(ruta)) as imagen:
            self.assertEqual((imagen.format, imagen.size), ("WEBP", (600, 480)))
        url_miniatura(producto.imagen, "icono")
        with Image.open(self.archivo(ruta_miniatura(producto.imagen.name, "icono"))) as icono:
            self.assertEqual(icono.size, (160, 128))

    def test_la_de_compartir_es_jpeg(self):
        producto = self.con_foto()
        self.assertTrue(url_miniatura(producto.imagen, "compartir").endswith(".jpg"))
        with Image.open(self.archivo(ruta_miniatura(producto.imagen.name, "compartir"))) as imagen:
            self.assertEqual(imagen.format, "JPEG")

    def test_no_agranda_fotos_chicas(self):
        producto = self.crear_producto(imagen=foto("chica.png", 100, 100))
        url_miniatura(producto.imagen)
        with Image.open(self.archivo(ruta_miniatura(producto.imagen.name, "tarjeta"))) as imagen:
            self.assertEqual(imagen.size, (100, 100))

    def test_si_falta_la_original_usa_la_original(self):
        producto = self.con_foto()
        os.remove(self.archivo(producto.imagen.name))
        self.assertEqual(url_miniatura(producto.imagen), producto.imagen.url)

    def test_al_cambiar_la_foto_se_borran_sus_miniaturas(self):
        producto = self.con_foto()
        url_miniatura(producto.imagen)
        vieja = self.archivo(ruta_miniatura(producto.imagen.name, "tarjeta"))
        self.assertTrue(vieja.exists())
        with self.captureOnCommitCallbacks(execute=True):
            producto.imagen = foto("nueva.png")
            producto.save()
        self.assertFalse(vieja.exists())

    def test_al_eliminar_el_producto_y_sus_fotos(self):
        producto = self.con_foto()
        extra = FotoProducto.objects.create(producto=producto, imagen=foto("extra.png"), orden=1)
        miniaturas = [ruta_miniatura(producto.imagen.name, "tarjeta"), ruta_miniatura(extra.imagen.name, "icono")]
        url_miniatura(producto.imagen)
        url_miniatura(extra.imagen, "icono")
        with self.captureOnCommitCallbacks(execute=True):
            producto.delete()
        for ruta in miniaturas:
            self.assertFalse(default_storage.exists(ruta), ruta)

    def test_borrar_una_miniatura_no_borra_otra_cosa(self):
        producto = self.con_foto()
        url_miniatura(producto.imagen)
        default_storage.delete(ruta_miniatura(producto.imagen.name, "tarjeta"))
        self.assertTrue(self.archivo(producto.imagen.name).exists())

    def test_las_paginas_usan_miniaturas(self):
        producto = self.con_foto(activo=True)
        tarjeta = url_miniatura(producto.imagen)
        for url in (reverse("inicio"), reverse("catalogo:catalogo"), reverse("tiendas:perfil", args=[self.tienda.pk])):
            respuesta = self.client.get(url)
            self.assertContains(respuesta, f'<img src="{tarjeta}"', msg_prefix=url)
            self.assertNotContains(respuesta, f'src="{producto.imagen.url}"', msg_prefix=url)

    def test_favoritos_usa_miniatura(self):
        from django.contrib.auth.models import Group, User

        cliente = User.objects.create_user("cli", "cli@ejemplo.com", "ClaveSegura#2026")
        cliente.groups.add(Group.objects.get(name="Cliente"))
        producto = self.con_foto(activo=True)
        Favorito.objects.create(usuario=cliente, producto=producto, precio_guardado=producto.precio, precio_visto=producto.precio)
        self.client.force_login(cliente)
        self.assertContains(self.client.get(reverse("favoritos:lista")), f'src="{url_miniatura(producto.imagen)}"')

    def test_el_detalle_usa_la_grande_y_miniaturas_en_la_fila(self):
        producto = self.con_foto(activo=True)
        FotoProducto.objects.create(producto=producto, imagen=foto("extra.png"), orden=1)
        respuesta = self.client.get(reverse("catalogo:detalle", args=[producto.pk]))
        self.assertContains(respuesta, f'data-ampliar="{producto.imagen.url}"')  # la grande, para ver de cerca
        self.assertContains(respuesta, f'<img src="{url_miniatura(producto.imagen, "icono")}" alt="" width="64"')

    def test_comando_crea_todas(self):
        producto = self.con_foto()
        call_command("crear_miniaturas", stdout=open(os.devnull, "w"))
        for tipo in ("tarjeta", "icono", "compartir"):
            self.assertTrue(self.archivo(ruta_miniatura(producto.imagen.name, tipo)).exists(), tipo)
