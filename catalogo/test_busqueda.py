"""Pruebas de la búsqueda sin tildes."""

from django.test import SimpleTestCase
from django.urls import reverse

from .busqueda import normalizar
from .models import Marca, Producto
from .tests import BaseCatalogo


class NormalizarTests(SimpleTestCase):
    def test_quita_tildes_mayusculas_y_espacios(self):
        self.assertEqual(normalizar("  Cámara   ÑANDÚ "), "camara nandu")


class BusquedaSinTildesTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.crear_producto(nombre="Cámara Sony Alpha", descripcion="Lente de 50 mm")
        self.crear_producto(nombre="Audífonos inalámbricos")

    def buscar(self, texto):
        respuesta = self.client.get(reverse("catalogo:catalogo"), {"q": texto})
        return [p.nombre for p in respuesta.context["pagina"]]

    def test_sin_tilde_encuentra_con_tilde(self):
        self.assertEqual(self.buscar("camara"), ["Cámara Sony Alpha"])
        self.assertEqual(self.buscar("audifonos"), ["Audífonos inalámbricos"])

    def test_con_tilde_y_mayusculas(self):
        self.assertEqual(self.buscar("CÁMARA"), ["Cámara Sony Alpha"])

    def test_varias_palabras_en_cualquier_orden(self):
        self.assertEqual(self.buscar("sony camara"), ["Cámara Sony Alpha"])
        self.assertEqual(self.buscar("sony audifonos"), [])

    def test_busca_en_descripcion_marca_y_categoria(self):
        self.assertIn("Cámara Sony Alpha", self.buscar("lente"))
        self.assertEqual(len(self.buscar("samsung")), 2)  # marca de ambos productos
        self.assertEqual(len(self.buscar("celulares")), 2)  # categoría

    def test_renombrar_la_marca_actualiza_la_busqueda(self):
        marca = Marca.objects.get(nombre="Samsung")
        marca.nombre = "Samsúng Electronics"
        marca.save()
        self.assertEqual(len(self.buscar("samsung electronics")), 2)

    def test_mis_productos_tambien_busca_sin_tildes(self):
        self.client.force_login(self.tienda.usuario)
        respuesta = self.client.get(reverse("catalogo:mis_productos"), {"q": "camara"})
        self.assertContains(respuesta, "Cámara Sony Alpha")
        self.assertNotContains(respuesta, "Audífonos")

    def test_el_texto_se_guarda_normalizado(self):
        producto = Producto.objects.get(nombre="Cámara Sony Alpha")
        self.assertIn("camara sony alpha", producto.texto_busqueda)
