"""
Diseño celeste (nov 2026): estilos base, cabecera, pie e Inicio como la vista previa aprobada, la consola del
administrador (menú lateral de vidrio) y los correos. Reemplazó por completo al estilo «Carbón y oro».
"""

from datetime import datetime
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from catalogo.tests import BaseCatalogo, crear_tienda
from tiendas.inicio import fecha_y_hora, tiendas_para_inicio
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
        self.assertIn("logo-marca logo-marca--caja", pie)

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


class CabeceraTests(TestCase):
    def test_visitante_con_botones_de_acceso_en_la_segunda_fila(self):
        html = self.client.get(reverse("inicio")).content.decode()
        fila = html[html.index('class="menu-acceso'):]
        fila = fila[:fila.index("</div>")]
        for texto in ("Iniciar sesión", "Registrarse", "Registrar mi tienda"):
            self.assertIn(texto, fila)
        self.assertIn('class="icono-cuenta"', html)  # círculo de la persona arriba a la derecha
        self.assertNotIn("corazon-cabecera", html)
        self.assertIn('class="barra-categorias"', html)

    def test_buscador_con_lupa_y_boton_buscar(self):
        html = self.client.get(reverse("inicio")).content.decode()
        self.assertIn('placeholder="Buscar productos..."', html)
        self.assertIn('class="buscador-menu__lupa"', html)
        self.assertIn('<span class="d-none d-lg-inline" aria-hidden="true">Buscar</span>', html)

    def test_logo_en_cuadro_azul(self):
        html = self.client.get(reverse("inicio")).content.decode()
        self.assertIn('<span class="logo-marca logo-marca--caja">', html)
        self.assertIn('<span class="logo-marca__tec">Tec</span>', html)

    def test_secciones_con_iconos(self):
        html = self.client.get(reverse("inicio")).content.decode()
        for icono, texto in (("house", "Inicio"), ("grid", "Catálogo"), ("geo-alt", "Tiendas cercanas")):
            self.assertIn(f'<i class="bi bi-{icono}" aria-hidden="true"></i> {texto}</a>', html)

    def test_cliente_sin_favoritos_no_muestra_contador(self):
        cliente = User.objects.create_user("cliente1", password="Clave#2026")
        cliente.groups.add(Group.objects.get_or_create(name="Cliente")[0])
        self.client.force_login(cliente)
        html = self.client.get(reverse("inicio")).content.decode()
        self.assertIn('aria-label="Mis favoritos (0)"', html)
        self.assertNotIn("corazon-cabecera__contador", html)
        self.assertNotIn('class="menu-acceso', html)


class EstilosTests(TestCase):
    def test_fondo_celeste_en_todo_el_sitio(self):
        css = leer_estatico("css/marca.css")
        self.assertIn("100. Diseño celeste", css)
        self.assertIn("--cel-grad: linear-gradient(135deg, #2C86F7, #1460D9);", css)
        self.assertIn("body.fondo-marca.fondo-marca{", css)
        # «Carbón y oro» ya no se usa en ninguna parte (tampoco en la consola).
        self.assertNotIn("--nx-carbon", css)
        self.assertNotIn("fondo-vetas.svg", css)
        self.assertNotIn("consola-cuerpo)", css)

    def test_letra_inter_dentro_del_proyecto(self):
        fuentes = leer_estatico("vendor/fuentes/fuentes.css")
        for peso in ("400", "500", "600", "700"):
            self.assertIn(f'url("inter-{peso}.woff")', fuentes)
            archivo = finders.find(f"vendor/fuentes/inter-{peso}.woff")
            self.assertIsNotNone(archivo, peso)
            with open(archivo, "rb") as letra:
                self.assertEqual(letra.read(4), b"wOFF")
        self.assertIsNotNone(finders.find("vendor/fuentes/LICENSE-inter"))

    def test_colores_por_marca(self):
        css = leer_estatico("css/marca.css")
        for marca in ("samsung", "lenovo", "xiaomi", "apple", "epson", "kingston"):
            self.assertIn(f".chip-marca--{marca}", css)


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
        self.assertNotIn('class="franja-tiendas"', html)  # la franja «¿Tienes una tienda…?» no es para tiendas


class TarjetaDeProductoTests(BaseCatalogo):
    def test_boton_de_whatsapp_y_marca_de_color(self):
        self.crear_producto()
        html = self.client.get(reverse("inicio")).content.decode()
        self.assertIn('class="chip-marca chip-marca--samsung">Samsung</span>', html)
        self.assertIn('class="btn btn-wa tarjeta-producto__whatsapp"', html)
        self.assertIn('<span class="d-none d-sm-inline">Consultar por </span>WhatsApp', html)
        self.assertIn('href="https://wa.me/51911111111?text=', html)

    def test_agotado_pregunta_cuando_llega(self):
        self.crear_producto(stock=0)
        html = self.client.get(reverse("inicio")).content.decode()
        self.assertIn('<span class="tarjeta-producto__agotado">Agotado</span>', html)
        self.assertIn('class="btn btn-wa-borde tarjeta-producto__whatsapp"', html)
        self.assertIn("¿Cuándo llega?", html)

    def test_oferta_con_descuento_sobre_la_foto(self):
        from decimal import Decimal

        self.crear_producto(precio=Decimal("250.00"), precio_oferta=Decimal("200.00"))
        html = self.client.get(reverse("inicio")).content.decode()
        self.assertIn('<span class="tarjeta-producto__descuento">-20%</span>', html)


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
        self.assertNotContains(respuesta, "etiqueta-oro")
        self.assertContains(respuesta, "Así funciona NEXALYS Tec")
        self.assertContains(respuesta, "Escribe por WhatsApp")
        self.assertContains(respuesta, 'class="franja-tiendas"')  # el visitante ve la franja para tiendas

    def test_categorias_van_primero(self):
        self.crear_producto()  # el panel de categorías solo sale si hay productos publicados
        html = self.client.get(reverse("inicio")).content.decode()
        self.assertLess(html.index('class="categorias-inicio'), html.index('class="tiendas-inicio'))

    def test_las_suspendidas_no_salen(self):
        self.tienda.suspender("Prueba")
        _, total = tiendas_para_inicio()
        self.assertEqual(total, 8)


class FechaYHoraTests(TestCase):
    def test_texto_con_hora_de_peru(self):
        momento = timezone.make_aware(datetime(2026, 11, 17, 18, 52))
        self.assertEqual(fecha_y_hora(momento), "Martes 17 de noviembre · 6:52 p. m.")
        temprano = timezone.make_aware(datetime(2026, 1, 4, 9, 5))
        self.assertEqual(fecha_y_hora(temprano), "Domingo 4 de enero · 9:05 a. m.")

    def test_sale_bajo_el_titulo(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, '<p class="tiendas-inicio__fecha">')


class ConsolaCelesteTests(TestCase):
    def setUp(self):
        from administracion.test_consola import crear_admin

        self.client.force_login(crear_admin())

    def test_cabecera_con_logo_en_cuadro_azul(self):
        html = self.client.get(reverse("panel_admin")).content.decode()
        cabecera = html[html.index('<header class="cabecera-consola"'):html.index("</header>")]
        self.assertIn('<span class="logo-marca logo-marca--caja">', cabecera)
        self.assertIn('class="btn-close" data-bs-dismiss="offcanvas"', html)

    def test_menu_lateral_de_vidrio_y_grafico_en_azul(self):
        css = leer_estatico("css/marca.css")
        self.assertIn("Consola del administrador en celeste", css)
        self.assertIn("body.fondo-marca .consola__nav a.activo{ background: var(--cel-grad);", css)
        html = self.client.get(reverse("panel_admin")).content.decode()
        self.assertIn('var azul = estilos.getPropertyValue("--cel-azul").trim() || "#1F7BF2";', html)


class CorreosCelestesTests(TestCase):
    def test_diseno_celeste_en_los_correos(self):
        from django.core import mail

        from config import correos

        correos.enviar(["a@ejemplo.com"], "Prueba", "correos/prueba")
        html = next(contenido for contenido, tipo in mail.outbox[0].alternatives if tipo == "text/html")
        self.assertIn('<body style="margin:0;padding:0;background:#EEF5FE;">', html)
        self.assertIn("background-image:linear-gradient(135deg,#2C86F7,#1460D9)", html)  # franja de arriba
        self.assertIn('bgcolor="#1A6FE8"', html)  # Outlook: azul liso
        self.assertIn('bgcolor="#0B1B3A"', html)  # cuadrito del logo con la «N»
        self.assertIn('NEXALYS <span style="color:#BFE9FF;">Tec</span>', html)
