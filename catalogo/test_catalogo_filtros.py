"""Catálogo con filtros a la izquierda, íconos de categorías y visor claro."""

from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.urls import reverse

from .models import Categoria, Marca
from .tests import BaseCatalogo


class CatalogoFiltrosTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.url = reverse("catalogo:catalogo")
        self.xiaomi, _ = Marca.objects.get_or_create(nombre="Xiaomi")
        self.audio, _ = Categoria.objects.get_or_create(nombre="Audio")
        self.a15 = self.crear_producto(nombre="Galaxy A15", precio=Decimal("700"), stock=3)
        self.note = self.crear_producto(nombre="Redmi Note 14", marca=self.xiaomi, precio=Decimal("950"), stock=0)
        self.buds = self.crear_producto(tienda=self.otra_tienda, nombre="Redmi Buds 6", marca=self.xiaomi,
                                        categoria=self.audio, precio=Decimal("109"), precio_oferta=Decimal("99"))

    def nombres(self, **filtros):
        respuesta = self.client.get(self.url, filtros)
        return respuesta, sorted(p.nombre for p in respuesta.context["pagina"])

    def test_varias_marcas_y_tiendas_a_la_vez(self):
        _, nombres = self.nombres(marca=[self.marca.pk, self.xiaomi.pk])
        self.assertEqual(nombres, ["Galaxy A15", "Redmi Buds 6", "Redmi Note 14"])
        _, nombres = self.nombres(tienda=[self.otra_tienda.pk])
        self.assertEqual(nombres, ["Redmi Buds 6"])

    def test_cada_opcion_muestra_cuantos_productos_tiene(self):
        respuesta = self.client.get(self.url, {"categoria": self.categoria.pk})
        marcas = {m["nombre"]: m["cantidad"] for m in respuesta.context["marcas"]}
        self.assertEqual(marcas, {"Samsung": 1, "Xiaomi": 1})
        self.assertEqual(respuesta.context["disponibilidad"]["en_stock"], 1)
        self.assertEqual(respuesta.context["precio"], {"minimo": 700, "maximo": 950})

    def test_las_marcas_se_cuentan_sin_su_propio_filtro(self):
        # Con Samsung elegida, Xiaomi sigue apareciendo con sus productos para poder sumarla.
        respuesta = self.client.get(self.url, {"marca": self.marca.pk})
        marcas = {m["nombre"]: (m["cantidad"], m["elegida"]) for m in respuesta.context["marcas"]}
        self.assertEqual(marcas, {"Samsung": (1, True), "Xiaomi": (2, False)})

    def test_solo_en_stock_y_ofertas(self):
        _, nombres = self.nombres(en_stock="on")
        self.assertNotIn("Redmi Note 14", nombres)
        _, nombres = self.nombres(solo_ofertas="on")
        self.assertEqual(nombres, ["Redmi Buds 6"])

    def test_titulo_ruta_y_chips_para_quitar_filtros(self):
        respuesta = self.client.get(self.url, {"categoria": self.audio.pk, "marca": self.xiaomi.pk})
        self.assertContains(respuesta, '<h1 class="h3 mb-0">Audio</h1>', html=True)
        self.assertContains(respuesta, '<span aria-current="page">Audio</span>', html=True)
        chips = {c["texto"]: c["url"] for c in respuesta.context["chips"]}
        self.assertEqual(chips["Xiaomi"], f"{self.url}?categoria={self.audio.pk}")
        self.assertEqual(chips["Audio"], f"{self.url}?marca={self.xiaomi.pk}")
        self.assertContains(respuesta, "Quitar todos")

    def test_la_busqueda_viene_del_menu_y_se_conserva(self):
        respuesta = self.client.get(self.url, {"q": "redmi"})
        self.assertContains(respuesta, "Resultados para «redmi»")
        self.assertContains(respuesta, '<input type="hidden" name="q" value="redmi">', html=True)
        self.assertNotContains(respuesta, 'name="categoria" class="form-select')  # la categoría está en la barra

    def test_sin_resultados_ofrece_ver_todo(self):
        respuesta = self.client.get(self.url, {"q": "zzzz"})
        self.assertContains(respuesta, "No encontramos productos con esos filtros")

    def test_filtros_y_vistas_en_la_pagina(self):
        respuesta = self.client.get(self.url)
        for parte in ('id="panel-filtros"', "data-rango", 'data-vista-boton="lista"', "js/catalogo.js",
                      'form="filtros-catalogo"', "Ver resultados"):
            self.assertContains(respuesta, parte)


class IconosCategoriaTests(BaseCatalogo):
    def test_la_lista_de_categorias_muestra_su_icono(self):
        Categoria.objects.filter(pk=self.categoria.pk).update(icono="phone")
        self.crear_producto()
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, '<i class="bi bi-phone" aria-hidden="true"></i>Celulares', html=False)
        self.assertContains(respuesta, "bootstrap-icons")

    def test_las_categorias_existentes_tienen_icono(self):
        # La migración les puso un ícono según su nombre.
        self.assertEqual(Categoria.objects.get(nombre="Celulares").icono, "phone")

    def test_el_admin_elige_el_icono(self):
        admin = User.objects.create_user("jefe", "j@ejemplo.com", "ClaveSegura#2026")
        admin.groups.add(Group.objects.get_or_create(name="Administrador")[0])
        self.client.force_login(admin)
        respuesta = self.client.get(reverse("catalogo:gestion_crear", args=["categorias"]))
        self.assertContains(respuesta, 'class="selector-icono"')
        self.client.post(reverse("catalogo:gestion_crear", args=["categorias"]),
                         {"nombre": "Drones", "icono": "camera", "activa": "on"})
        self.assertEqual(Categoria.objects.get(nombre="Drones").icono, "camera")


class VisorClaroTests(BaseCatalogo):
    def test_visor_con_fondo_claro_y_miniaturas(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, 'class="modal fade visor"')
        self.assertContains(respuesta, 'id="visor-miniaturas"')
        self.assertNotContains(respuesta, "bg-dark border-0")


class IconosAlCargarDatosTests(BaseCatalogo):
    def test_las_categorias_creadas_por_la_presentacion_traen_su_icono(self):
        import io

        from django.core.management import call_command

        Categoria.objects.filter(nombre="Pantallas").delete()
        call_command("cargar_productos_presentacion", stdout=io.StringIO())
        self.assertEqual(Categoria.objects.get(nombre="Pantallas").icono, "display")
