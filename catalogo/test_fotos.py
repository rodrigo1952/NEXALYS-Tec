"""Pruebas de varias fotos por producto y de la optimización de imágenes."""

import io
import os
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from .models import MAX_FOTOS_EXTRA, FotoProducto, Producto
from .tests import BaseCatalogo

CARPETA_MEDIA = tempfile.mkdtemp()


def foto(nombre="foto.png", ancho=200, alto=200, color="green"):
    archivo = io.BytesIO()
    Image.new("RGB", (ancho, alto), color).save(archivo, "PNG")
    return SimpleUploadedFile(nombre, archivo.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=CARPETA_MEDIA)
class FotosProductoTests(BaseCatalogo):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.client.force_login(self.tienda.usuario)

    def test_crear_producto_con_varias_fotos(self):
        respuesta = self.client.post(reverse("catalogo:crear"), self.datos_formulario(
            imagen=foto("principal.png"), fotos_nuevas=[foto("a.png"), foto("b.png")],
        ))
        self.assertRedirects(respuesta, reverse("catalogo:mis_productos"))
        producto = Producto.objects.get()
        self.assertEqual(producto.fotos.count(), 2)
        self.assertTrue(all(f.imagen.name.endswith(".webp") for f in producto.fotos.all()))

    def test_limite_de_fotos_adicionales(self):
        fotos = [foto(f"f{numero}.png") for numero in range(MAX_FOTOS_EXTRA + 1)]
        respuesta = self.client.post(reverse("catalogo:crear"), self.datos_formulario(fotos_nuevas=fotos))
        self.assertIn("fotos_nuevas", respuesta.context["form"].errors)
        self.assertFalse(Producto.objects.exists())

    def test_archivo_que_no_es_imagen_se_rechaza(self):
        falso = SimpleUploadedFile("virus.png", b"no soy una imagen", content_type="image/png")
        respuesta = self.client.post(reverse("catalogo:crear"), self.datos_formulario(fotos_nuevas=[falso]))
        self.assertIn("fotos_nuevas", respuesta.context["form"].errors)

    def test_quitar_una_foto(self):
        producto = self.crear_producto()
        quedarse = FotoProducto.objects.create(producto=producto, imagen=foto("queda.png"), orden=1)
        quitar = FotoProducto.objects.create(producto=producto, imagen=foto("sale.png"), orden=2)
        ruta = quitar.imagen.path
        url = reverse("catalogo:editar", args=[producto.pk])
        version = self.client.get(url).context["form"]["version"].value()

        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(url, self.datos_formulario(
                nombre="Galaxy A15", version=version, eliminar_fotos=[quitar.pk],
            ))
        self.assertRedirects(respuesta, reverse("catalogo:mis_productos"))
        self.assertEqual(list(producto.fotos.all()), [quedarse])
        self.assertFalse(os.path.exists(ruta))  # también se borró el archivo

    def test_detalle_muestra_la_galeria(self):
        producto = self.crear_producto(imagen=foto("principal.png"))
        FotoProducto.objects.create(producto=producto, imagen=foto("extra.png"))
        respuesta = self.client.get(reverse("catalogo:detalle", args=[producto.pk]))
        self.assertEqual(len(respuesta.context["fotos"]), 2)
        self.assertContains(respuesta, 'id="galeria"')

    def test_eliminar_el_producto_borra_sus_fotos(self):
        producto = self.crear_producto()
        extra = FotoProducto.objects.create(producto=producto, imagen=foto("extra.png"))
        ruta = extra.imagen.path
        with self.captureOnCommitCallbacks(execute=True):
            producto.delete()
        self.assertFalse(os.path.exists(ruta))

    # --- Optimización -----------------------------------------------------------
    def test_la_foto_principal_se_reduce_y_pasa_a_webp(self):
        producto = self.crear_producto(imagen=foto("grande.png", ancho=2400, alto=1600))
        self.assertTrue(producto.imagen.name.endswith(".webp"))
        with Image.open(producto.imagen.path) as guardada:
            self.assertEqual(guardada.size, (1200, 800))  # se mantiene la proporción

    def test_una_foto_pequena_no_se_agranda(self):
        producto = self.crear_producto(imagen=foto("chica.png", ancho=300, alto=200))
        with Image.open(producto.imagen.path) as guardada:
            self.assertEqual(guardada.size, (300, 200))
