"""
Páginas más claras en el celular (nov 2026): menú lateral, rangos rápidos de precio, categorías del inicio
y «Mis productos» como tarjetas.
"""

from decimal import Decimal

from django.urls import reverse

from .test_consistencia import leer_estatico
from .tests import BaseCatalogo


class RangosDePrecioTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        for nombre, precio in (("Funda", "35"), ("Audífonos", "250"), ("Celular", "899"), ("Laptop", "2499")):
            self.crear_producto(nombre=nombre, precio=Decimal(precio))
        self.url = reverse("catalogo:catalogo")

    def rangos(self, **parametros):
        return {r["texto"]: r for r in self.client.get(self.url, parametros).context["rangos_precio"]}

    def test_muestra_los_rangos_con_productos_y_su_cantidad(self):
        rangos = self.rangos()
        self.assertEqual({t: r["cantidad"] for t, r in rangos.items()},
                         {"Hasta S/ 100": 1, "S/ 100 a 500": 1, "S/ 500 a 1,500": 1, "S/ 1,500 a 3,000": 1})
        self.assertNotIn("Más de S/ 3,000", rangos)  # sin productos: no se muestra
        self.assertIn("precio_min=500", rangos["S/ 500 a 1,500"]["url"])
        self.assertIn("precio_max=1500", rangos["S/ 500 a 1,500"]["url"])
        self.assertNotIn("precio_min", rangos["Hasta S/ 100"]["url"])

    def test_el_rango_elegido_se_marca_y_su_enlace_lo_quita(self):
        respuesta = self.client.get(self.url, {"precio_min": "500", "precio_max": "1500"})
        self.assertEqual([p.nombre for p in respuesta.context["pagina"]], ["Celular"])
        rango = {r["texto"]: r for r in respuesta.context["rangos_precio"]}["S/ 500 a 1,500"]
        self.assertTrue(rango["activo"])
        self.assertNotIn("precio", rango["url"])
        self.assertContains(respuesta, 'class="chip-rango activo"')

    def test_los_rangos_respetan_los_demas_filtros(self):
        rangos = self.rangos(q="laptop")
        self.assertEqual(list(rangos), ["S/ 1,500 a 3,000"])

    def test_en_el_panel_de_filtros_el_precio_va_primero(self):
        html = self.client.get(self.url).content.decode()
        self.assertLess(html.index("<summary>Precio</summary>"), html.index("<summary>Disponibilidad</summary>"))


class MenuDelCelularTests(BaseCatalogo):
    def test_invitado_ve_botones_para_entrar_y_crear_cuenta(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, 'id="menu-movil"')
        self.assertContains(respuesta, 'data-bs-target="#menu-movil"')
        self.assertContains(respuesta, 'class="btn btn-acento w-100 menu-movil__boton"')
        self.assertContains(respuesta, "Crear cuenta")
        self.assertNotContains(respuesta, "data-menu-cerrar-sesion")

    def test_la_tienda_ve_sus_secciones_y_cerrar_sesion(self):
        self.client.force_login(self.tienda.usuario)
        respuesta = self.client.get(reverse("catalogo:mis_productos"))
        self.assertContains(respuesta, "Datos de mi tienda")
        self.assertContains(respuesta, 'class="menu-movil__enlace activo"', html=False)
        self.assertContains(respuesta, "data-menu-cerrar-sesion")
        self.assertContains(respuesta, 'class="cuenta-movil d-lg-none"')


class InicioYMisProductosTests(BaseCatalogo):
    def test_inicio_con_categorias_y_2_productos_por_fila(self):
        self.crear_producto()
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, "categorias-inicio__enlace")
        self.assertContains(respuesta, "row row-cols-2 row-cols-lg-4")

    def test_mis_productos_trae_lo_que_usan_las_tarjetas(self):
        self.crear_producto()
        self.client.force_login(self.tienda.usuario)
        respuesta = self.client.get(reverse("catalogo:mis_productos"))
        for texto in ('data-etiqueta="Precio"', 'data-etiqueta="Stock"', "celda-acciones", "celda-favoritos", "fila-deslizable"):
            self.assertContains(respuesta, texto)

    def test_estilos_del_celular(self):
        css = leer_estatico("css/marca.css")
        for regla in (".menu-movil__enlace.activo", ".chip-rango.activo", ".categorias-inicio__lista",
                      "top: var(--cabecera-visible, 0px);",
                      '"producto producto" "precio stock" "estado favoritos" "acciones acciones"'):
            self.assertIn(regla, css)
