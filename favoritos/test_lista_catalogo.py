"""Mis favoritos con la forma del catálogo: filtros a la izquierda y tarjetas que abren el producto."""

from django.urls import reverse

from catalogo.models import Categoria
from tiendas.models import Tienda

from .models import Favorito
from .tests import BaseFavoritos


class ListaComoCatalogoTests(BaseFavoritos):
    def setUp(self):
        super().setUp()
        Categoria.objects.filter(pk=self.categoria.pk).update(icono="phone")
        self.laptop = self.crear_producto(tienda=self.otra_tienda, nombre="Laptop X", categoria=self.otra_categoria)
        Favorito.guardar(self.cliente, self.producto)
        Favorito.guardar(self.cliente, self.laptop)
        self.client.force_login(self.cliente)
        self.url = reverse("favoritos:lista")

    def nombres(self, **filtros):
        respuesta = self.client.get(self.url, filtros)
        return sorted(f.producto.nombre for f in respuesta.context["pagina"])

    def test_filtros_a_la_izquierda_sin_boton_filtrar(self):
        respuesta = self.client.get(self.url)
        for parte in ('id="panel-filtros"', 'id="filtros-catalogo"', "js/catalogo.js", "Ver resultados",
                      'name="categoria" value="%d"' % self.categoria.pk, 'name="tienda" value="%d"' % self.otra_tienda.pk):
            self.assertContains(respuesta, parte)
        self.assertNotContains(respuesta, ">Filtrar</button>")
        self.assertNotContains(respuesta, "<select")

    def test_las_categorias_muestran_su_icono_y_cantidad(self):
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, '<i class="bi bi-phone" aria-hidden="true"></i>Celulares')
        categorias = {c["nombre"]: c["cantidad"] for c in respuesta.context["categorias"]}
        self.assertEqual(categorias, {"Celulares": 1, "Laptops": 1})

    def test_varias_categorias_y_tiendas_a_la_vez(self):
        self.assertEqual(self.nombres(categoria=[self.categoria.pk, self.otra_categoria.pk]), ["Galaxy A15", "Laptop X"])
        self.assertEqual(self.nombres(tienda=[self.otra_tienda.pk]), ["Laptop X"])
        self.assertEqual(self.nombres(categoria=[self.categoria.pk], tienda=[self.otra_tienda.pk]), [])

    def test_las_cantidades_respetan_el_otro_filtro(self):
        respuesta = self.client.get(self.url, {"tienda": self.tienda.pk})
        categorias = {c["nombre"]: (c["cantidad"], c["elegida"]) for c in respuesta.context["categorias"]}
        self.assertEqual(categorias, {"Celulares": (1, False)})
        tiendas = {t["nombre"]: t["elegida"] for t in respuesta.context["tiendas"]}
        self.assertEqual(tiendas, {"Tienda Uno": True, "Tienda Dos": False})
        self.assertContains(respuesta, "Quitar todos")

    def test_la_tarjeta_abre_el_producto_y_la_tienda(self):
        respuesta = self.client.get(self.url)
        detalle = reverse("catalogo:detalle", args=[self.producto.pk])
        self.assertContains(respuesta, f'<a href="{detalle}" class="tarjeta-producto__nombre stretched-link">Galaxy A15</a>', html=True)
        self.assertContains(respuesta, f'href="{reverse("tiendas:perfil", args=[self.tienda.pk])}" class="link-secondary"')
        self.assertContains(respuesta, 'class="catalogo-grilla" data-vista="3"')

    def test_quitar_pide_confirmacion(self):
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, 'id="modal-quitar-favorito"')
        self.assertContains(respuesta, "¿Quitar de favoritos?")
        self.assertContains(respuesta, "data-quitar-favorito data-nombre", count=2)
        self.assertContains(respuesta, reverse("favoritos:alternar", args=[self.producto.pk]))

    def test_no_disponible_sin_enlaces(self):
        Tienda.objects.filter(pk=self.tienda.pk).update(estado=Tienda.Estado.SUSPENDIDA)
        respuesta = self.client.get(self.url)
        self.assertNotContains(respuesta, reverse("catalogo:detalle", args=[self.producto.pk]))
        self.assertNotContains(respuesta, f'href="{reverse("tiendas:perfil", args=[self.tienda.pk])}"')
        self.assertContains(respuesta, "No disponible")

    def test_sin_favoritos(self):
        Favorito.objects.all().delete()
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, "Aún no guardaste productos")
        self.assertNotContains(respuesta, 'id="panel-filtros"')
