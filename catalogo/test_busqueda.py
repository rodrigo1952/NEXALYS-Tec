"""Pruebas de la búsqueda sin tildes."""

from datetime import timedelta

from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone

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


class BusquedaPorRelevanciaTests(BaseCatalogo):
    """Lo que coincide en el nombre sale primero; lo que solo está en la descripción, al final."""

    def setUp(self):
        super().setUp()
        # La laptop se crea DESPUÉS, así que con "Más recientes" saldría primero.
        self.teclado = self.crear_producto(nombre="Teclado Genius Smart KB-100")
        self.laptop = self.crear_producto(
            nombre="Laptop HP OmniBook 3", descripcion="Teclado en español retroiluminado, 16 GB RAM"
        )
        # Fechas fijas para que "Más recientes" no dependa de la velocidad de la PC.
        Producto.objects.filter(pk=self.teclado.pk).update(creado=timezone.now() - timedelta(days=1))

    def buscar(self, texto, **extra):
        respuesta = self.client.get(reverse("catalogo:catalogo"), {"q": texto, **extra})
        return respuesta, [p.nombre for p in respuesta.context["pagina"]]

    def test_al_buscar_ordena_por_relevancia(self):
        _, nombres = self.buscar("teclado")
        self.assertEqual(nombres, ["Teclado Genius Smart KB-100", "Laptop HP OmniBook 3"])

    def test_sigue_buscando_en_la_descripcion(self):
        _, nombres = self.buscar("retroiluminado")
        self.assertEqual(nombres, ["Laptop HP OmniBook 3"])

    def test_sin_busqueda_ordena_por_recientes(self):
        respuesta = self.client.get(reverse("catalogo:catalogo"))
        nombres = [p.nombre for p in respuesta.context["pagina"]]
        self.assertEqual(nombres.index("Laptop HP OmniBook 3"), 0)

    def test_el_usuario_puede_elegir_otro_orden(self):
        _, nombres = self.buscar("teclado", orden="recientes")
        self.assertEqual(nombres[0], "Laptop HP OmniBook 3")

    def test_etiqueta_solo_en_coincidencias_por_descripcion(self):
        respuesta, _ = self.buscar("teclado")
        productos = {p.nombre: p for p in respuesta.context["pagina"]}
        self.assertFalse(productos["Teclado Genius Smart KB-100"].coincide_descripcion)
        self.assertTrue(productos["Laptop HP OmniBook 3"].coincide_descripcion)
        self.assertContains(respuesta, "Coincide con sus características", count=1)

    def test_coincidir_por_marca_no_muestra_la_etiqueta(self):
        respuesta, nombres = self.buscar("samsung")  # marca de ambos productos
        self.assertEqual(len(nombres), 2)
        self.assertNotContains(respuesta, "Coincide con sus características")

    def test_varias_palabras_prefiere_mas_coincidencias_en_el_nombre(self):
        self.crear_producto(nombre="Teclado Logitech K120")
        _, nombres = self.buscar("teclado genius")
        self.assertEqual(nombres, ["Teclado Genius Smart KB-100"])
        _, nombres = self.buscar("teclado")
        self.assertEqual(nombres[-1], "Laptop HP OmniBook 3")

    def test_sin_buscar_no_aparece_la_etiqueta(self):
        respuesta = self.client.get(reverse("catalogo:catalogo"))
        self.assertNotContains(respuesta, "Coincide con sus características")

    def test_campos_de_busqueda_separados(self):
        self.assertEqual(self.laptop.nombre_busqueda, "laptop hp omnibook 3")
        self.assertIn("samsung", self.laptop.etiquetas_busqueda)
        self.assertNotIn("teclado", self.laptop.nombre_busqueda)
