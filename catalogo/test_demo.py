"""Etapa 4: exportar y cargar los datos de demostración."""

import io
import json
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from PIL import Image

from tiendas.models import HorarioDia, Tienda

from . import demo
from .models import FotoProducto, Producto
from .tests import BaseCatalogo

CARPETA_MEDIA = tempfile.mkdtemp()


def png(nombre="foto.png"):
    archivo = io.BytesIO()
    Image.new("RGB", (30, 30), "blue").save(archivo, "PNG")
    return SimpleUploadedFile(nombre, archivo.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=CARPETA_MEDIA)
class DemoTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.carpeta = Path(tempfile.mkdtemp())
        self.producto = self.crear_producto(
            nombre="Laptop Demo", imagen=png(), precio=Decimal("2500.00"), precio_oferta=Decimal("2300.00"),
            destacado=True,
        )
        FotoProducto.objects.create(producto=self.producto, imagen=png(), orden=1)
        HorarioDia.objects.create(tienda=self.tienda, dia=0)

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)
        super().tearDown()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def exportar_y_vaciar(self):
        call_command("exportar_demo", "--carpeta", str(self.carpeta), stdout=io.StringIO())
        # Simula otra PC: base de datos sin esas tiendas.
        User.objects.filter(tienda__isnull=False).delete()

    def test_exporta_sin_correos_reales_ni_contrasenas(self):
        call_command("exportar_demo", "--carpeta", str(self.carpeta), stdout=io.StringIO())
        texto = (self.carpeta / "datos.json").read_text(encoding="utf-8")
        datos = json.loads(texto)
        self.assertEqual(len(datos["tiendas"]), 2)
        self.assertEqual(datos["productos"][0]["nombre"], "Laptop Demo")
        self.assertNotIn("@ejemplo.com", texto)
        self.assertNotIn("pbkdf2", texto)
        self.assertTrue((self.carpeta / "imagenes" / datos["productos"][0]["imagen"]).exists())

    def test_cargar_crea_tiendas_productos_e_imagenes(self):
        self.exportar_y_vaciar()
        salida = io.StringIO()
        call_command("cargar_demo", "--carpeta", str(self.carpeta), stdout=salida)
        tienda = Tienda.objects.get(nombre="Tienda Uno")
        producto = Producto.objects.get(nombre="Laptop Demo")
        self.assertEqual(producto.tienda, tienda)
        self.assertEqual(producto.precio_oferta, Decimal("2300.00"))
        self.assertTrue(producto.destacado)
        self.assertTrue(producto.imagen.name.startswith(f"tiendas/{tienda.pk}-tienda-uno/productos/"))
        self.assertTrue(producto.imagen.storage.exists(producto.imagen.name))
        self.assertEqual(producto.fotos.count(), 1)
        self.assertEqual(tienda.horarios.count(), 1)
        self.assertTrue(self.client.login(username="tienda1", password=demo.CLAVE_DEMO))
        self.assertIn(demo.CLAVE_DEMO, salida.getvalue())

    def test_cargar_dos_veces_no_duplica(self):
        self.exportar_y_vaciar()
        call_command("cargar_demo", "--carpeta", str(self.carpeta), stdout=io.StringIO())
        salida = io.StringIO()
        call_command("cargar_demo", "--carpeta", str(self.carpeta), stdout=salida)
        self.assertEqual(Producto.objects.filter(nombre="Laptop Demo").count(), 1)
        self.assertIn("Ya existe en esta PC", salida.getvalue())

    def test_crea_admin_si_no_hay_ninguno(self):
        self.exportar_y_vaciar()
        call_command("cargar_demo", "--carpeta", str(self.carpeta), stdout=io.StringIO())
        self.assertTrue(User.objects.filter(username="admin", is_superuser=True).exists())

    def test_sin_exportacion_da_un_mensaje_claro(self):
        from django.core.management.base import CommandError

        with self.assertRaisesMessage(CommandError, "exportar_demo"):
            call_command("cargar_demo", "--carpeta", str(self.carpeta / "no-existe"), stdout=io.StringIO())
