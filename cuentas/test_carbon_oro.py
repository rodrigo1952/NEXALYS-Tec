"""
Estilo «Carbón y oro», fase 1 (nov 2026): fondo carbón con vetas doradas, colores según el contexto
(oscuro o tarjeta blanca), encabezado según el rol y pie con la columna «Contacto».
"""

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings
from django.urls import reverse


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
