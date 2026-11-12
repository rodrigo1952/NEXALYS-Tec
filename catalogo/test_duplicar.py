"""«Duplicar producto»: abre un producto nuevo con los datos de otro (sin stock, fotos ni código)."""

import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from inventario.models import FichaInventario

from .models import Marca, Producto
from .tests import BaseCatalogo, imagen_png

CARPETA_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=CARPETA_MEDIA)
class DuplicarProductoTests(BaseCatalogo):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.original = self.crear_producto(
            nombre="Galaxy A15 128 GB", descripcion="Pantalla 6.5\"", precio=Decimal("699.90"),
            precio_oferta=Decimal("649.90"), oferta_hasta=timezone.localdate() + timedelta(days=5),
            stock=7, destacado=True, imagen=imagen_png(),
        )
        FichaInventario.objects.update_or_create(
            producto=self.original, defaults={"costo": Decimal("520.00"), "stock_minimo": 2, "codigo": "GAL-A15"}
        )
        self.client.force_login(self.tienda.usuario)
        self.url = reverse("catalogo:crear") + f"?copiar={self.original.pk}"

    def inicial(self, respuesta):
        form = respuesta.context["form"]
        return {nombre: form[nombre].value() for nombre in form.fields}

    def test_el_formulario_llega_lleno_menos_stock_fotos_y_codigo(self):
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, "Duplicar producto")
        self.assertContains(respuesta, "Es una copia de <strong>Galaxy A15 128 GB</strong>")
        datos = self.inicial(respuesta)
        self.assertEqual(datos["nombre"], "Galaxy A15 128 GB (copia)")
        self.assertEqual(datos["categoria"], self.categoria.pk)
        self.assertEqual(datos["marca"], self.marca.pk)
        self.assertEqual(datos["precio"], Decimal("699.90"))
        self.assertEqual(datos["precio_oferta"], Decimal("649.90"))
        self.assertEqual(datos["descripcion"], "Pantalla 6.5\"")
        self.assertEqual(datos["precio_compra"], Decimal("520.00"))
        self.assertEqual(datos["stock_minimo"], 2)
        self.assertEqual(datos["stock"], 0)
        self.assertFalse(datos["activo"])
        self.assertFalse(datos["destacado"])
        self.assertIn(datos["codigo"], ("", None))
        self.assertEqual(respuesta.context["form"].fotos_galeria(), [])  # sin fotos

    def test_al_guardar_se_crea_otro_producto_sin_publicar_y_el_original_no_cambia(self):
        respuesta = self.client.post(self.url, self.datos_formulario(
            nombre="Galaxy A15 256 GB", precio="799.90", stock="0", activo="", precio_compra="600",
        ), follow=True)
        self.assertContains(respuesta, "La copia está sin publicar")
        copia = Producto.objects.get(nombre="Galaxy A15 256 GB")
        self.assertFalse(copia.activo)
        self.assertEqual(copia.stock, 0)
        self.assertFalse(copia.imagen)
        self.assertEqual(copia.ficha.costo, Decimal("600.00"))
        self.original.refresh_from_db()
        self.assertEqual((self.original.nombre, self.original.stock), ("Galaxy A15 128 GB", 7))
        self.assertTrue(self.original.imagen)
        self.assertEqual(self.original.ficha.codigo, "GAL-A15")

    def test_no_se_puede_duplicar_un_producto_de_otra_tienda(self):
        ajeno = self.crear_producto(tienda=self.otra_tienda, nombre="Ajeno")
        self.assertEqual(self.client.get(reverse("catalogo:crear") + f"?copiar={ajeno.pk}").status_code, 404)

    def test_oferta_vencida_y_marca_desactivada_no_se_copian(self):
        apagada = Marca.objects.create(nombre="Marca vieja", activa=False)
        Producto.objects.filter(pk=self.original.pk).update(
            marca=apagada, oferta_hasta=timezone.localdate() - timedelta(days=1)
        )
        datos = self.inicial(self.client.get(self.url))
        self.assertIsNone(datos["marca"])
        self.assertIsNone(datos["precio_oferta"])
        self.assertIsNone(datos["oferta_hasta"])

    def test_nombre_largo_no_pasa_el_maximo(self):
        Producto.objects.filter(pk=self.original.pk).update(nombre="X" * 150)
        nombre = self.inicial(self.client.get(self.url))["nombre"]
        self.assertEqual(len(nombre), 150)
        self.assertTrue(nombre.endswith(" (copia)"))

    def test_boton_duplicar_en_la_lista_y_al_editar(self):
        enlace = f"{reverse('catalogo:crear')}?copiar={self.original.pk}"
        self.assertContains(self.client.get(reverse("catalogo:mis_productos")), enlace)
        self.assertContains(self.client.get(reverse("catalogo:editar", args=[self.original.pk])), enlace)

    def test_copiar_invalido_abre_el_formulario_vacio(self):
        respuesta = self.client.get(reverse("catalogo:crear") + "?copiar=abc")
        self.assertContains(respuesta, "Agregar producto")
