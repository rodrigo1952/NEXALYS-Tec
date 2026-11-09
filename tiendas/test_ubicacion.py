"""Tiendas cercanas: ubicación del local en el mapa (OpenStreetMap), lista por distancia y «Cómo llegar»."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Marca, Producto

from .models import Tienda


class BaseUbicacion(TestCase):
    def crear_tienda(self, nombre, whatsapp, estado=Tienda.Estado.ACTIVA, **datos):
        usuario = User.objects.create_user(nombre.lower().replace(" ", ""), password="Clave#2026")
        return Tienda.objects.create(usuario=usuario, nombre=nombre, direccion="Jr. Espinar, Quillabamba",
                                     whatsapp=whatsapp, estado=estado, **datos)


class TiendasCercanasTests(BaseUbicacion):
    def setUp(self):
        self.con_mapa = self.crear_tienda("Zeta Tech", "911111111", latitud=Decimal("-12.866500"), longitud=Decimal("-72.692800"))
        self.sin_mapa = self.crear_tienda("Alfa Tech", "922222222")
        self.pendiente = self.crear_tienda("Pendiente Tech", "933333333", estado=Tienda.Estado.PENDIENTE)
        categoria, marca = Categoria.objects.get_or_create(nombre="Laptops")[0], Marca.objects.get_or_create(nombre="Lenovo")[0]
        Producto.objects.create(tienda=self.con_mapa, categoria=categoria, marca=marca, nombre="IdeaPad", precio=Decimal("1000"), stock=1)
        Producto.objects.create(tienda=self.con_mapa, categoria=categoria, marca=marca, nombre="Oculto", precio=Decimal("1000"), stock=1, activo=False)

    def test_es_publica_y_solo_muestra_tiendas_activas(self):
        respuesta = self.client.get(reverse("tiendas:cercanas"))
        self.assertEqual(respuesta.status_code, 200)
        nombres = [t["nombre"] for t in respuesta.context["tiendas"]]
        self.assertEqual(nombres, ["Zeta Tech", "Alfa Tech"])  # primero las que marcaron su local
        self.assertNotIn("Pendiente Tech", respuesta.content.decode())

    def test_datos_para_el_mapa(self):
        respuesta = self.client.get(reverse("tiendas:cercanas"))
        zeta, alfa = respuesta.context["tiendas"]
        self.assertEqual((zeta["lat"], zeta["lng"]), (-12.8665, -72.6928))
        self.assertEqual(zeta["productos"], 1)  # solo los publicados
        self.assertEqual(zeta["como_llegar"], "https://www.google.com/maps/dir/?api=1&destination=-12.866500,-72.692800")
        self.assertIsNone(alfa["lat"])
        # Sin punto marcado, «Cómo llegar» igual traza la ruta hacia la dirección escrita.
        self.assertEqual(alfa["como_llegar"], "https://www.google.com/maps/dir/?api=1&destination=Jr.%20Espinar%2C%20Quillabamba")
        self.assertContains(respuesta, 'id="datos-tiendas"')
        self.assertContains(respuesta, "Aún no marcaron su local en el mapa", count=1)
        self.assertContains(respuesta, "leaflet/1.9.4/leaflet.js")
        self.assertContains(respuesta, 'data-centro-lat="-12.86806"')  # con punto, no con coma

    def test_openstreetmap_recibe_el_dominio(self):
        # Django manda «same-origin» por defecto; OpenStreetMap necesita saber el sitio (Referer).
        for url in (reverse("tiendas:cercanas"), reverse("tiendas:perfil", args=[self.con_mapa.pk])):
            self.assertEqual(self.client.get(url)["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertEqual(self.client.get(reverse("catalogo:catalogo"))["Referrer-Policy"], "same-origin")

    def test_enlace_en_el_menu_para_todos(self):
        self.assertContains(self.client.get(reverse("inicio")), reverse("tiendas:cercanas"))
        self.client.force_login(self.con_mapa.usuario)
        html = self.client.get(reverse("catalogo:catalogo")).content.decode()
        menu = html[html.index("menu-secciones"):html.index("</ul>", html.index("menu-secciones"))]
        self.assertIn("Tiendas cercanas", menu)

    def test_perfil_con_ubicacion_tiene_mapa_y_como_llegar(self):
        respuesta = self.client.get(reverse("tiendas:perfil", args=[self.con_mapa.pk]))
        self.assertContains(respuesta, "Cómo llegar")
        self.assertContains(respuesta, 'data-lat="-12.866500" data-lng="-72.692800"')
        sin = self.client.get(reverse("tiendas:perfil", args=[self.sin_mapa.pk]))
        self.assertContains(sin, "Ver en Google Maps")
        self.assertNotContains(sin, "data-mapa-tienda")


class MarcarUbicacionTests(BaseUbicacion):
    def setUp(self):
        self.tienda = self.crear_tienda("Kantu Tech", "944444444")
        self.client.force_login(self.tienda.usuario)
        self.url = reverse("tiendas:editar")

    def datos(self, **cambios):
        datos = {
            "datos-nombre": "Kantu Tech", "datos-direccion": "Jr. Espinar, Quillabamba", "datos-whatsapp": "944444444",
            "datos-descripcion": "", "datos-latitud": "", "datos-longitud": "",
        }
        datos.update(cambios)
        return datos

    def test_el_editor_tiene_el_mapa(self):
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, "data-mapa-editar")
        self.assertContains(respuesta, 'data-latitud="id_datos-latitud"')
        self.assertContains(respuesta, "Usar mi ubicación actual")

    def test_marcar_el_local_pide_la_contrasena(self):
        respuesta = self.client.post(self.url, self.datos(**{"datos-latitud": "-12.869000", "datos-longitud": "-72.691500"}))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "escribe tu contraseña actual")
        self.tienda.refresh_from_db()
        self.assertFalse(self.tienda.tiene_ubicacion)
        respuesta = self.client.post(self.url, self.datos(**{
            "datos-latitud": "-12.869000", "datos-longitud": "-72.691500", "datos-clave_actual": "Clave#2026"}))
        self.assertRedirects(respuesta, reverse("tiendas:panel"))
        self.tienda.refresh_from_db()
        self.assertEqual((self.tienda.latitud, self.tienda.longitud), (Decimal("-12.869000"), Decimal("-72.691500")))

    def test_la_ubicacion_va_completa_y_dentro_del_rango(self):
        respuesta = self.client.post(self.url, self.datos(**{"datos-latitud": "-12.869000", "datos-clave_actual": "Clave#2026"}))
        self.assertContains(respuesta, "La ubicación en el mapa quedó incompleta")
        respuesta = self.client.post(self.url, self.datos(**{
            "datos-latitud": "-120", "datos-longitud": "-72.69", "datos-clave_actual": "Clave#2026"}))
        self.assertEqual(respuesta.status_code, 200)
        self.tienda.refresh_from_db()
        self.assertFalse(self.tienda.tiene_ubicacion)

    def test_quitar_la_ubicacion(self):
        Tienda.objects.filter(pk=self.tienda.pk).update(latitud=Decimal("-12.869"), longitud=Decimal("-72.6915"))
        self.client.post(self.url, self.datos(**{"datos-clave_actual": "Clave#2026"}))
        self.tienda.refresh_from_db()
        self.assertFalse(self.tienda.tiene_ubicacion)

    def test_la_contrasena_menciona_la_ubicacion_una_sola_vez(self):
        texto = self.client.get(self.url).content.decode()
        self.assertEqual(texto.count("ubicación en el mapa"), 1)
