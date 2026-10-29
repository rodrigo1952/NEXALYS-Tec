"""Galería de fotos al editar un producto: un botón para cada cambio, aplicados al guardar."""

import os
import shutil
import tempfile

from django.test import override_settings
from django.urls import reverse
from PIL import Image

from .models import FotoProducto, Producto
from .test_fotos import foto
from .tests import BaseCatalogo

CARPETA_MEDIA = tempfile.mkdtemp()


def color(campo):
    """Color dominante del centro de la imagen guardada ("rojo" o "verde")."""
    with campo.storage.open(campo.name, "rb") as archivo:
        r, g, _ = Image.open(archivo).convert("RGB").getpixel((5, 5))
    return "rojo" if r > g else "verde"


@override_settings(MEDIA_ROOT=CARPETA_MEDIA)
class GaleriaEdicionTests(BaseCatalogo):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.client.force_login(self.tienda.usuario)
        self.producto = self.crear_producto(imagen=foto("principal.png", color="red"))
        self.adicional = FotoProducto.objects.create(producto=self.producto, imagen=foto("extra.png"), orden=1)
        self.url = reverse("catalogo:editar", args=[self.producto.pk])

    def guardar(self, **cambios):
        version = self.client.get(self.url).context["form"]["version"].value()
        datos = self.datos_formulario(nombre="Galaxy A15", version=version)
        datos.update(cambios)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.url, datos)

    def test_la_galeria_muestra_todas_las_fotos_con_sus_botones(self):
        respuesta = self.client.get(self.url)
        for texto in ("Fotos del producto", "Foto principal", "Cambiar foto principal", 'aria-label="Quitar la foto principal"',
                      "Hacer principal", "Reemplazar", 'aria-label="Quitar la foto 1"', "+ Agregar fotos",
                      "Puedes agregar 4 más", "o arrástralas aquí"):
            self.assertContains(respuesta, texto)
        self.assertContains(respuesta, self.adicional.imagen.url)
        self.assertContains(respuesta, f'name="reemplazar_{self.adicional.pk}"')

    def test_categoria_y_marca_en_una_fila(self):
        html = self.client.get(reverse("catalogo:crear")).content.decode()
        fila = html.index('<div class="row g-3 mb-3">')
        self.assertLess(fila, html.index('name="categoria"'))
        self.assertLess(html.index('name="categoria"'), html.index('name="marca"'))
        self.assertLess(html.index('name="marca"'), html.index('name="codigo"'))

    def test_hacer_principal_intercambia_las_fotos(self):
        respuesta = self.guardar(principal_foto=str(self.adicional.pk))
        self.assertRedirects(respuesta, reverse("catalogo:mis_productos"))
        self.producto.refresh_from_db()
        self.adicional.refresh_from_db()
        # La principal era roja y la adicional verde: ahora es al revés.
        self.assertEqual(color(self.producto.imagen), "verde")
        self.assertEqual(color(self.adicional.imagen), "rojo")
        self.assertTrue(self.producto.imagen.storage.exists(self.producto.imagen.name))
        self.assertTrue(self.adicional.imagen.storage.exists(self.adicional.imagen.name))
        self.assertNotEqual(self.producto.imagen.name, self.adicional.imagen.name)

    def test_hacer_principal_sin_foto_principal(self):
        Producto.objects.filter(pk=self.producto.pk).update(imagen="")
        self.guardar(principal_foto=str(self.adicional.pk))
        self.producto.refresh_from_db()
        self.assertTrue(self.producto.imagen.name)
        self.assertFalse(self.producto.fotos.exists())  # la adicional subió a principal
        self.assertTrue(self.producto.imagen.storage.exists(self.producto.imagen.name))

    def test_reemplazar_una_foto_adicional(self):
        anterior = self.adicional.imagen.path
        self.guardar(**{f"reemplazar_{self.adicional.pk}": foto("nueva.png", color="blue")})
        self.adicional.refresh_from_db()
        self.assertNotEqual(self.adicional.imagen.path, anterior)
        self.assertFalse(os.path.exists(anterior))  # el archivo viejo se borró

    def test_quitar_la_foto_principal(self):
        self.guardar(**{"imagen-clear": "on"})
        self.producto.refresh_from_db()
        self.assertFalse(self.producto.imagen)

    def test_no_se_puede_quitar_y_hacer_principal_a_la_vez(self):
        respuesta = self.guardar(principal_foto=str(self.adicional.pk), eliminar_fotos=[self.adicional.pk])
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No puedes quitar la foto que elegiste como principal")

    def test_agregar_fotos_al_editar(self):
        self.guardar(fotos_nuevas=[foto("a.png"), foto("b.png")])
        self.assertEqual(self.producto.fotos.count(), 3)

    def test_la_principal_va_grande_y_las_adicionales_aparte(self):
        html = self.client.get(self.url).content.decode()
        principal = html.index('class="tarjeta-foto tarjeta-foto--principal"')
        secundarias = html.index('class="galeria-edicion__secundarias"')
        self.assertLess(principal, secundarias)
        self.assertLess(secundarias, html.index('class="tarjeta-foto tarjeta-foto--secundaria"'))

    def test_arrastrar_y_quitar_con_x(self):
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, 'draggable="true"')  # las adicionales se arrastran a la principal
        self.assertContains(respuesta, 'data-soltar-texto="Suelta para que sea la foto principal"')
        self.assertContains(respuesta, 'class="zona-agregar mb-0" data-zona-agregar')
        self.assertContains(respuesta, 'class="tarjeta-foto__x"', count=2)
        self.assertNotContains(respuesta, "modal-quitar-foto")  # la X no pide confirmación: se deshace

    def test_sin_espacio_no_hay_zona_para_agregar(self):
        for orden in range(2, 6):
            FotoProducto.objects.create(producto=self.producto, imagen=foto(f"extra{orden}.png"), orden=orden)
        respuesta = self.client.get(self.url)
        self.assertNotContains(respuesta, 'class="zona-agregar')
        self.assertContains(respuesta, "Ya tienes el máximo de fotos adicionales")

    def test_el_visor_recorre_las_fotos_del_producto(self):
        respuesta = self.client.get(reverse("catalogo:detalle", args=[self.producto.pk]))
        self.assertContains(respuesta, 'data-galeria="producto"', count=2)
        for parte in ('id="visor-anterior"', 'id="visor-siguiente"', 'id="visor-contador"'):
            self.assertContains(respuesta, parte)
