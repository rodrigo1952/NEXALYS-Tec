"""
Nov 2026: el logo se elige como las fotos de los productos (círculo, clic o arrastrar, vista previa) y el
mapa para marcar el local tiene «Ampliar mapa», «Mapa / Satélite» y «Buscar» una calle.
"""

import shutil
import tempfile

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings
from django.urls import reverse

from .test_editar import imagen
from .tests import crear_tienda

CARPETA_MEDIA = tempfile.mkdtemp()


def estatico(ruta):
    with open(finders.find(ruta), encoding="utf-8") as archivo:
        return archivo.read()


@override_settings(MEDIA_ROOT=CARPETA_MEDIA)
class CampoLogoTests(TestCase):
    url = reverse("tiendas:editar")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.tienda = crear_tienda()
        self.client.force_login(self.tienda.usuario)

    def datos(self, **cambios):
        return {"datos-nombre": self.tienda.nombre, "datos-direccion": self.tienda.direccion,
                "datos-whatsapp": self.tienda.whatsapp, "datos-descripcion": "", **cambios}

    def test_sin_logo_muestra_el_circulo_con_la_inicial(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn("data-campo-logo", html)
        self.assertIn('name="datos-logo"', html)
        self.assertIn('name="datos-logo-clear"', html)
        self.assertIn("Elegir imagen", html)
        self.assertIn("arrastra una imagen", html)
        self.assertNotIn("Actualmente", html)  # ya no sale el texto del campo de Django
        self.assertNotIn("Quitar logo", html.split('id="form-logo"')[0])  # sin logo no hay nada que quitar
        self.assertIn("js/campo_logo.js", html)

    def test_cambiar_el_logo_sin_contrasena(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.url, self.datos(**{"datos-logo": imagen()}))
        self.tienda.refresh_from_db()
        self.assertTrue(self.tienda.logo)
        html = self.client.get(self.url).content.decode()
        self.assertIn(f'src="{self.tienda.logo.url}"', html)
        self.assertIn("Cambiar logo", html)
        self.assertIn("Quitar logo", html)

    def test_quitar_el_logo_con_la_casilla(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.url, self.datos(**{"datos-logo": imagen()}))
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.url, self.datos(**{"datos-logo-clear": "on"}))
        self.tienda.refresh_from_db()
        self.assertFalse(self.tienda.logo)

    def test_la_ventana_del_menu_usa_el_mismo_campo(self):
        html = self.client.get(reverse("mi_cuenta")).content.decode()
        ventana = html.split('id="form-logo"')[1]
        self.assertIn("data-campo-logo", ventana)
        self.assertIn('name="logo"', ventana)
        self.assertIn("data-logo-guardar disabled", ventana)

    def test_el_script(self):
        codigo = estatico("js/campo_logo.js")
        for texto in ('campo.addEventListener("drop"', "new DataTransfer()", "La imagen pesa más de 2 MB",
                      "Elige una imagen JPG, PNG o WEBP.", "deshacer.addEventListener"):
            self.assertIn(texto, codigo)


class MapaDelLocalTests(TestCase):
    def setUp(self):
        self.tienda = crear_tienda()
        self.client.force_login(self.tienda.usuario)

    def test_botones_del_editor(self):
        html = self.client.get(reverse("tiendas:editar")).content.decode()
        for texto in ("data-editor-ubicacion", "data-buscar-direccion", "data-buscar-boton", "Ampliar mapa",
                      "data-cerrar-mapa", "Marca tu local en el mapa"):
            self.assertIn(texto, html)

    def test_satelite_busqueda_y_pantalla_completa_en_el_script(self):
        codigo = estatico("js/mapas.js")
        self.assertIn("World_Imagery/MapServer/tile/{z}/{y}/{x}", codigo)
        self.assertIn("Imágenes &copy; Esri", codigo)
        self.assertIn('"https://nominatim.openstreetmap.org/search"', codigo)
        self.assertIn('bounded: "1"', codigo)
        self.assertIn("1100", codigo)  # máximo una búsqueda por segundo
        self.assertIn("editor-ubicacion--ampliado", codigo)
        self.assertIn('evento.key === "Escape"', codigo)

    def test_reducir_mapa_y_abreviaturas(self):
        html = self.client.get(reverse("tiendas:editar")).content.decode()
        self.assertIn("Reducir mapa</button>", html)
        self.assertNotIn("Listo</button>", html)
        codigo = estatico("js/mapas.js")
        self.assertIn('enElMapa.title = texto;', codigo)  # ⤢ / ⤡ en la esquina del mapa
        self.assertIn('[/\\bjr\\b\\.?/g, "jirón"]', codigo)
        self.assertIn("function sinTipoDeVia(texto)", codigo)
        self.assertIn("esperar(1100)", codigo)  # el segundo intento respeta 1 búsqueda por segundo

    def test_la_politica_de_seguridad_permite_esos_servicios(self):
        self.assertIn("https://server.arcgisonline.com", settings.SECURE_CSP["img-src"])
        self.assertIn("https://nominatim.openstreetmap.org", settings.SECURE_CSP["connect-src"])
