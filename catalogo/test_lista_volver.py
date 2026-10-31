"""Mis productos: volver a la misma página al editar, filtro «Ocultos», páginas con números y fotos nuevas."""

from django.core.paginator import Paginator
from django.template import Context, Template
from django.test import SimpleTestCase
from django.urls import reverse

from .models import Producto
from .tests import BaseCatalogo


class VolverALaMismaPaginaTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.tienda.usuario)
        for numero in range(12):  # 2 páginas (10 por página)
            self.crear_producto(nombre=f"Producto {numero:02d}")
        self.producto = Producto.objects.get(nombre="Producto 11")
        self.editar = reverse("catalogo:editar", args=[self.producto.pk])

    def guardar(self, lista):
        version = self.client.get(self.editar, {"lista": lista}).context["form"]["version"].value()
        datos = self.datos_formulario(nombre="Producto 11", version=version, lista=lista)
        return self.client.post(self.editar, datos)

    def test_los_enlaces_llevan_la_pagina_y_los_filtros(self):
        respuesta = self.client.get(reverse("catalogo:mis_productos"), {"page": 2, "q": "producto"})
        self.assertContains(respuesta, f'{self.editar}?lista=page%3D2%26q%3Dproducto"')
        self.assertContains(respuesta, f'id="producto-{self.producto.pk}"')

    def test_al_guardar_vuelve_a_la_misma_pagina_y_baja_al_producto(self):
        respuesta = self.guardar("page=2&ver=bajo")
        self.assertRedirects(
            respuesta, f'{reverse("catalogo:mis_productos")}?page=2&ver=bajo#producto-{self.producto.pk}',
            fetch_redirect_response=False,
        )

    def test_cancelar_tambien_vuelve(self):
        respuesta = self.client.get(self.editar, {"lista": "page=2"})
        self.assertContains(respuesta, f'href="{reverse("catalogo:mis_productos")}?page=2#producto-{self.producto.pk}"')
        self.assertContains(respuesta, '<input type="hidden" name="lista" value="page=2">', html=True)

    def test_solo_se_aceptan_filtros_conocidos(self):
        respuesta = self.guardar("page=2&next=https://otro.sitio&ver=bajo")
        self.assertEqual(respuesta["Location"], f'{reverse("catalogo:mis_productos")}?page=2&ver=bajo#producto-{self.producto.pk}')

    def test_sin_lista_vuelve_al_inicio_de_la_lista(self):
        respuesta = self.guardar("")
        self.assertEqual(respuesta["Location"], f'{reverse("catalogo:mis_productos")}#producto-{self.producto.pk}')

    def test_eliminar_vuelve_a_la_misma_pagina(self):
        url = reverse("catalogo:eliminar", args=[self.producto.pk])
        self.assertContains(self.client.get(url, {"lista": "page=2"}), f'?page=2#producto-{self.producto.pk}"')
        respuesta = self.client.post(url, {"lista": "page=2"})
        self.assertEqual(respuesta["Location"], f'{reverse("catalogo:mis_productos")}?page=2')

    def test_numeros_de_pagina(self):
        respuesta = self.client.get(reverse("catalogo:mis_productos"), {"page": 2})
        self.assertContains(respuesta, 'aria-label="Ir a la página 1"')
        self.assertContains(respuesta, '<span class="page-link">2<span class="visually-hidden"> (página actual)</span></span>', html=True)
        self.assertContains(respuesta, "Página 2 de 2")


class FiltroOcultosTests(BaseCatalogo):
    def test_ocultos_por_la_tienda_y_por_el_administrador(self):
        self.client.force_login(self.tienda.usuario)
        self.crear_producto(nombre="Visible")
        self.crear_producto(nombre="Despublicado", activo=False)
        self.crear_producto(nombre="Ocultado", oculto_por_admin=True, motivo_ocultamiento="Precio falso")
        respuesta = self.client.get(reverse("catalogo:mis_productos"), {"ver": "ocultos"})
        self.assertEqual(sorted(p.nombre for p in respuesta.context["pagina"]), ["Despublicado", "Ocultado"])
        self.assertEqual(respuesta.context["resumen"]["ocultos"], 2)
        self.assertContains(respuesta, 'Ocultos <span class="contador">2</span>', html=False)
        self.assertContains(respuesta, "Estos productos no se ven en el catálogo", count=1)
        otra = self.client.get(reverse("catalogo:mis_productos"), {"ver": "sin_costo"})
        self.assertNotContains(otra, "Estos productos no se ven en el catálogo")
        self.assertContains(otra, 'filtro-rapido--aviso activo" aria-current="true">Sin precio de compra')


class PaginasRecortadasTests(SimpleTestCase):
    def numeros(self, total, actual):
        pagina = Paginator(range(total * 10), 10).get_page(actual)
        html = Template("{% load formato %}{% numeros_de_pagina pagina as n %}{{ n|join:',' }}").render(Context({"pagina": pagina}))
        return html

    def test_hasta_siete_se_ven_todas(self):
        self.assertEqual(self.numeros(7, 1), "1,2,3,4,5,6,7")

    def test_muchas_se_recortan(self):
        self.assertEqual(self.numeros(30, 10), f"1,{Paginator.ELLIPSIS},8,9,10,11,12,{Paginator.ELLIPSIS},30")


class FotosNuevasComoTarjetasTests(BaseCatalogo):
    def test_las_fotos_nuevas_se_ven_junto_a_las_adicionales(self):
        self.client.force_login(self.tienda.usuario)
        producto = self.crear_producto()
        respuesta = self.client.get(reverse("catalogo:editar", args=[producto.pk]))
        self.assertContains(respuesta, "tarjeta-foto--nueva")
        self.assertContains(respuesta, 'etiqueta.textContent = "Nueva"')
        self.assertNotContains(respuesta, 'id="nuevas-fotos-lista"')
