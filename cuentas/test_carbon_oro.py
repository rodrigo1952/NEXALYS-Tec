"""
Estilo «Carbón y oro», fase 1 (nov 2026): fondo carbón con vetas doradas, colores según el contexto
(oscuro o tarjeta blanca), encabezado según el rol y pie con la columna «Contacto».
"""

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.staticfiles import finders
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from catalogo.tests import BaseCatalogo, crear_tienda
from tiendas.inicio import tiendas_para_inicio
from tiendas.models import Tienda


def leer_estatico(ruta):
    with open(finders.find(ruta), encoding="utf-8") as archivo:
        return archivo.read()


class PieDePaginaTests(TestCase):
    def pie(self):
        html = self.client.get(reverse("inicio")).content.decode()
        return html[html.index('<footer class="pie-marca'):html.index("</footer>")]

    def test_cuatro_columnas_con_contacto(self):
        pie = self.pie()
        for titulo in ("Explorar", "Para tiendas", "Contacto"):
            self.assertIn(f'<h2 class="pie-marca__titulo">{titulo}</h2>', pie)
        self.assertIn("Productos tecnológicos de las tiendas de tu ciudad.", pie)
        self.assertIn("Proyecto IV ciclo · IESTP Urusayhua · 2026", pie)

    def test_contacto_mantiene_los_enlaces_legales(self):
        # Libro de Reclamaciones (Indecopi) y Privacidad (Ley 29733) deben estar a la vista en todo el sitio.
        pie = self.pie()
        for nombre in ("ayuda", "privacidad", "reclamos:libro"):
            self.assertIn(f'href="{reverse(nombre)}"', pie)
        self.assertIn("Libro de Reclamaciones", pie)

    @override_settings(CORREO_SOPORTE="ayuda@mi-tienda.pe")
    def test_el_correo_sale_del_env(self):
        self.assertIn('href="mailto:ayuda@mi-tienda.pe"', self.pie())

    def test_correo_por_defecto(self):
        self.assertIn(f'mailto:{settings.CORREO_SOPORTE}', self.pie())


class EncabezadoSegunElRolTests(TestCase):
    def test_visitante(self):
        html = self.client.get(reverse("inicio")).content.decode()
        self.assertIn("Registrar mi tienda", html)
        self.assertNotIn("corazon-cabecera", html)
        self.assertIn('class="barra-categorias"', html)

    def test_cliente_sin_favoritos_no_muestra_contador(self):
        cliente = User.objects.create_user("cliente1", password="Clave#2026")
        cliente.groups.add(Group.objects.get_or_create(name="Cliente")[0])
        self.client.force_login(cliente)
        html = self.client.get(reverse("inicio")).content.decode()
        self.assertIn('aria-label="Mis favoritos (0)"', html)
        self.assertNotIn("corazon-cabecera__contador", html)


class EstilosTests(TestCase):
    def test_fondo_y_contextos(self):
        css = leer_estatico("css/marca.css")
        self.assertIn('url("../img/fondo-vetas.svg")', css)
        self.assertIn("--nx-carbon: #0E1218", css)
        self.assertIn("--nx-oro: #C8A468", css)
        self.assertIn(".contexto-claro, .card,", css)
        self.assertIn(".contexto-oscuro,", css)
        self.assertIn(".btn-oro {", css)
        self.assertIsNotNone(finders.find("img/fondo-vetas.svg"))

    def test_al_imprimir_la_hoja_es_blanca(self):
        css = leer_estatico("css/marca.css")
        bloque = css[css.rindex("Impresión: hoja blanca"):]
        self.assertIn(".fondo-marca { background: #fff !important; }", bloque)


class CorazonDelClienteTests(BaseCatalogo):
    def test_cliente_con_corazon_y_cantidad(self):
        from favoritos.models import Favorito

        cliente = User.objects.create_user("cliente9", password="Clave#2026")
        cliente.groups.add(Group.objects.get_or_create(name="Cliente")[0])
        Favorito.guardar(cliente, self.crear_producto())
        self.client.force_login(cliente)
        html = self.client.get(reverse("inicio")).content.decode()
        self.assertIn('aria-label="Mis favoritos (1)"', html)
        self.assertIn('<span class="corazon-cabecera__contador" aria-hidden="true">1</span>', html)


class MenuDeLaTiendaTests(BaseCatalogo):
    def test_mismo_orden_que_todos_y_con_categorias(self):
        # El usuario prefirió el orden de siempre (Inicio · Catálogo · Tiendas cercanas | Mis productos).
        self.client.force_login(self.tienda.usuario)
        html = self.client.get(reverse("inicio")).content.decode()
        menu = html[html.index('class="navbar-nav menu-secciones'):]
        orden = [menu.index(f'href="{reverse(n)}"') for n in ("inicio", "catalogo:catalogo", "tiendas:cercanas", "catalogo:mis_productos")]
        self.assertEqual(orden, sorted(orden))
        self.assertIn('class="barra-categorias"', html)


def estado(abierto, detalle, refrigerio=False):
    return {"abierto": abierto, "refrigerio": refrigerio, "detalle": detalle, "texto": ""}


class TiendasEnElInicioTests(BaseCatalogo):
    """«¿Qué tienda está abierta ahora?»: hasta 6, las abiertas primero (tiendas/inicio.py)."""

    def setUp(self):
        super().setUp()
        for i, nombre in enumerate(["Alfa", "Beta", "Gama", "Delta", "Épsilon", "Zeta", "Eta"]):
            crear_tienda(f"t{i}", nombre, f"93333333{i}")
        # Abiertas: Zeta y Beta; en refrigerio: Gama; sin horario: Tienda Uno, Tienda Dos y Eta; el resto cerradas.
        estados = {
            "Zeta": estado(True, "Cierra a las 7:00 p. m."),
            "Beta": estado(True, "Cierra a las 8:00 p. m."),
            "Gama": estado(False, "Vuelve a las 3:00 p. m.", refrigerio=True),
            "Alfa": estado(False, "Abre a las 9:00 a. m."),
            "Delta": estado(False, "Abre el lunes a las 9:00 a. m."),
            "Épsilon": estado(False, "Abre a las 10:00 a. m."),
        }
        parche = mock.patch.object(Tienda, "estado_atencion", lambda tienda, ahora=None: estados.get(tienda.nombre))
        parche.start()
        self.addCleanup(parche.stop)

    def test_abiertas_primero_y_maximo_seis(self):
        tiendas, total = tiendas_para_inicio()
        self.assertEqual(total, 9)
        self.assertEqual([t["tienda"].nombre for t in tiendas], ["Beta", "Zeta", "Alfa", "Delta", "Épsilon", "Gama"])
        self.assertEqual(tiendas[0]["estado"], "Abierto ahora · cierra a las 8:00 p. m.")
        self.assertEqual(tiendas[2]["estado"], "Cerrado · abre a las 9:00 a. m.")
        self.assertEqual(tiendas[5]["estado"], "En refrigerio · vuelve a las 3:00 p. m.")
        self.assertEqual(tiendas[0]["productos"], [])  # sin productos con stock, no hay fotos

    def test_bloque_en_el_inicio(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, "¿Qué tienda está abierta ahora?")
        self.assertContains(respuesta, '<li class="tienda-inicio">', count=6)
        self.assertContains(respuesta, "tienda-inicio__estado--abierto", count=2)
        self.assertContains(respuesta, f'href="{reverse("tiendas:cercanas")}?ubicacion=1"')
        self.assertContains(respuesta, "Ver todas las tiendas (9)")
        self.assertNotContains(respuesta, "portada-marca")
        self.assertNotContains(respuesta, "Bienvenido a NEXALYS Tec")
        self.assertContains(respuesta, "Escribe por WhatsApp")

    def test_las_suspendidas_no_salen(self):
        self.tienda.suspender("Prueba")
        _, total = tiendas_para_inicio()
        self.assertEqual(total, 8)
