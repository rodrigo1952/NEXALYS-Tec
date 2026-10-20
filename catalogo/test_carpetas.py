"""Etapa 1: imágenes en una carpeta por tienda y comando ordenar_imagenes."""

import io
import os
import shutil
import tempfile

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from PIL import Image

from .archivos import carpeta_tienda
from .models import FotoProducto, Producto
from .tests import BaseCatalogo

CARPETA_MEDIA = tempfile.mkdtemp()


def png(nombre="Captura de pantalla.png"):
    archivo = io.BytesIO()
    Image.new("RGB", (40, 40), "red").save(archivo, "PNG")
    return SimpleUploadedFile(nombre, archivo.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=CARPETA_MEDIA)
class CarpetasPorTiendaTests(BaseCatalogo):
    def setUp(self):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().setUp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def test_carpeta_con_numero_y_nombre_sin_tildes(self):
        self.tienda.nombre = "Tecnología Ñandú"
        self.assertEqual(carpeta_tienda(self.tienda), f"tiendas/{self.tienda.pk}-tecnologia-nandu")

    def test_imagen_del_producto_va_a_su_tienda_con_su_nombre(self):
        producto = self.crear_producto(nombre="Laptop Asus TUF A15", imagen=png())
        self.assertEqual(
            producto.imagen.name, f"tiendas/{self.tienda.pk}-tienda-uno/productos/laptop-asus-tuf-a15.webp"
        )

    def test_fotos_extra_y_logo(self):
        producto = self.crear_producto(nombre="Mouse VSG")
        foto = FotoProducto.objects.create(producto=producto, imagen=png(), orden=2)
        self.assertEqual(foto.imagen.name, f"tiendas/{self.tienda.pk}-tienda-uno/productos/fotos/mouse-vsg-foto-2.webp")
        self.tienda.logo = png("mi logo.png")
        self.tienda.save()
        self.assertEqual(self.tienda.logo.name, f"tiendas/{self.tienda.pk}-tienda-uno/logo/logo.webp")

    def test_cada_tienda_tiene_su_carpeta(self):
        uno = self.crear_producto(nombre="Galaxy A15", imagen=png())
        dos = self.crear_producto(tienda=self.otra_tienda, nombre="Galaxy A15", imagen=png())
        self.assertNotEqual(os.path.dirname(uno.imagen.name), os.path.dirname(dos.imagen.name))

    def test_ordenar_imagenes_mueve_las_antiguas(self):
        producto = self.crear_producto(nombre="Teclado Genius")
        almacenamiento = producto.imagen.storage
        viejo = almacenamiento.save("productos/Captura_de_pantalla.webp", ContentFile(b"imagen"))
        Producto.objects.filter(pk=producto.pk).update(imagen=viejo)

        call_command("ordenar_imagenes", "--simular", stdout=io.StringIO())
        self.assertTrue(almacenamiento.exists(viejo))  # simular no mueve nada

        call_command("ordenar_imagenes", stdout=io.StringIO())
        producto.refresh_from_db()
        self.assertEqual(producto.imagen.name, f"tiendas/{self.tienda.pk}-tienda-uno/productos/teclado-genius.webp")
        self.assertTrue(almacenamiento.exists(producto.imagen.name))
        self.assertFalse(almacenamiento.exists(viejo))

        salida = io.StringIO()
        call_command("ordenar_imagenes", stdout=salida)  # una segunda vez no hace nada
        self.assertIn("Ya estaban ordenadas: 1", salida.getvalue())

    def test_archivo_faltante_no_rompe_el_comando(self):
        producto = self.crear_producto(nombre="Sin archivo")
        Producto.objects.filter(pk=producto.pk).update(imagen="productos/no-existe.webp")
        salida = io.StringIO()
        call_command("ordenar_imagenes", stdout=salida)
        self.assertIn("no existen en esta PC: 1", salida.getvalue())


@override_settings(MEDIA_ROOT=CARPETA_MEDIA)
class CambioDeNombreTests(BaseCatalogo):
    """Opción A: al cambiar el nombre, las imágenes se mueven solas."""

    def setUp(self):
        # Carpeta limpia en cada prueba: los números de tienda se repiten entre pruebas.
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().setUp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def test_renombrar_producto_renombra_imagen_y_fotos(self):
        producto = self.crear_producto(nombre="Laptop HP", imagen=png())
        foto = FotoProducto.objects.create(producto=producto, imagen=png(), orden=1)
        viejo = producto.imagen.name
        with self.captureOnCommitCallbacks(execute=True):
            producto.nombre = "Laptop HP OmniBook 3"
            producto.save()
        producto.refresh_from_db()
        foto.refresh_from_db()
        carpeta = f"tiendas/{self.tienda.pk}-tienda-uno/productos"
        self.assertEqual(producto.imagen.name, f"{carpeta}/laptop-hp-omnibook-3.webp")
        self.assertEqual(foto.imagen.name, f"{carpeta}/fotos/laptop-hp-omnibook-3-foto-1.webp")
        self.assertTrue(producto.imagen.storage.exists(producto.imagen.name))
        self.assertFalse(producto.imagen.storage.exists(viejo))

    def test_renombrar_tienda_mueve_toda_su_carpeta(self):
        producto = self.crear_producto(nombre="Mouse Gamer", imagen=png())
        self.tienda.logo = png("logo.png")
        self.tienda.save()
        carpeta_vieja = os.path.join(CARPETA_MEDIA, f"tiendas/{self.tienda.pk}-tienda-uno")
        self.assertTrue(os.path.isdir(carpeta_vieja))

        with self.captureOnCommitCallbacks(execute=True):
            self.tienda.nombre = "Tecno Quillabamba"
            self.tienda.save()
        producto.refresh_from_db()
        self.tienda.refresh_from_db()
        nueva = f"tiendas/{self.tienda.pk}-tecno-quillabamba"
        self.assertEqual(producto.imagen.name, f"{nueva}/productos/mouse-gamer.webp")
        self.assertEqual(self.tienda.logo.name, f"{nueva}/logo/logo.webp")
        self.assertTrue(producto.imagen.storage.exists(producto.imagen.name))
        self.assertFalse(os.path.isdir(carpeta_vieja))  # la carpeta vieja vacía se borra

    def test_guardar_sin_cambiar_el_nombre_no_mueve_nada(self):
        producto = self.crear_producto(nombre="Teclado", imagen=png())
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            producto.stock = 3
            producto.save()
        self.assertEqual(callbacks, [])

    def test_si_falta_el_archivo_la_pagina_no_se_rompe(self):
        producto = self.crear_producto(nombre="Fantasma")
        Producto.objects.filter(pk=producto.pk).update(imagen="productos/no-existe.webp")
        producto.refresh_from_db()
        with self.captureOnCommitCallbacks(execute=True):
            producto.nombre = "Fantasma 2"
            producto.save()  # no lanza error
        producto.refresh_from_db()
        self.assertEqual(producto.imagen.name, "productos/no-existe.webp")
