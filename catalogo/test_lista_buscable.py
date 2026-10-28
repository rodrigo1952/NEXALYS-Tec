"""Categorías y marcas nuevas (migración 0009) y la lista con buscador del formulario de producto."""
from django.test import TestCase
from django.urls import reverse

from tiendas.tests import crear_tienda

from .models import Categoria, Marca, Producto
from .tests import BaseCatalogo


class CategoriasYMarcasNuevasTests(TestCase):
    def test_la_migracion_las_agrega(self):
        for nombre in ("Tablets", "Computadoras de escritorio", "Impresoras y suministros", "Repuestos",
                       "Seguridad y videovigilancia", "Otros"):
            self.assertTrue(Categoria.objects.filter(nombre=nombre).exists(), nombre)
        for nombre in ("Honor", "Motorola", "Sony", "TP-Link", "Kingston", "Epson", "Soundcore (Anker)", "ZTE"):
            self.assertTrue(Marca.objects.filter(nombre=nombre).exists(), nombre)
        self.assertGreaterEqual(Marca.objects.count(), 57)

    def test_no_hay_repetidas_sin_importar_mayusculas(self):
        nombres = [m.lower() for m in Marca.objects.values_list("nombre", flat=True)]
        self.assertEqual(len(nombres), len(set(nombres)))


class ListaBuscableTests(TestCase):
    def setUp(self):
        self.client.force_login(crear_tienda().usuario)
        self.respuesta = self.client.get(reverse("catalogo:crear"))

    def test_categoria_y_marca_tienen_buscador(self):
        self.assertContains(self.respuesta, 'data-buscable="Escribe la categoría…"')
        self.assertContains(self.respuesta, 'data-buscable="Escribe la marca o su inicial…"')
        self.assertContains(self.respuesta, "js/lista_buscable.js")

    def test_otra_y_otros_van_al_final(self):
        form = self.respuesta.context["form"]
        marcas = [m.nombre for m in form.fields["marca"].queryset]
        categorias = [c.nombre for c in form.fields["categoria"].queryset]
        self.assertEqual(marcas[-1], "Otra")
        self.assertEqual(categorias[-1], "Otros")
        # El resto sigue en orden alfabético.
        self.assertEqual(marcas[:-1], sorted(marcas[:-1], key=str.lower))


class GuardarConMarcaNuevaTests(BaseCatalogo):
    def test_se_guarda_un_producto_con_categoria_y_marca_nuevas(self):
        self.client.force_login(self.tienda.usuario)
        tablets, sony = Categoria.objects.get(nombre="Tablets"), Marca.objects.get(nombre="Sony")
        self.client.post(reverse("catalogo:crear"), self.datos_formulario(categoria=tablets.pk, marca=sony.pk))
        producto = Producto.objects.get(nombre="Galaxy A25")
        self.assertEqual((producto.categoria, producto.marca), (tablets, sony))
