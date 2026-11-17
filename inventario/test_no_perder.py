"""
Nov 2026: no perder lo escrito. «+ Nuevo proveedor» se registra en una ventanita sin salir del ingreso,
«+ Crear producto» guarda un borrador y vuelve con todo, aviso «¿Salir sin guardar?», borrador automático
y el mismo producto no puede ir en dos filas.
"""

from decimal import Decimal

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Marca, Producto
from tiendas.tests import crear_tienda

from .models import Proveedor


def estatico(ruta):
    with open(finders.find(ruta), encoding="utf-8") as archivo:
        return archivo.read()


class BaseInventario(TestCase):
    def setUp(self):
        self.tienda = crear_tienda()
        self.client.force_login(self.tienda.usuario)
        categoria, _ = Categoria.objects.get_or_create(nombre="Laptops")
        marca, _ = Marca.objects.get_or_create(nombre="Asus")
        self.producto = Producto.objects.create(tienda=self.tienda, categoria=categoria, marca=marca,
                                                nombre="Asus TUF A15", precio=Decimal("3790"), stock=4)


class ProveedorRapidoTests(BaseInventario):
    url = reverse("inventario:proveedor_rapido")

    def test_el_ingreso_trae_la_ventanita(self):
        html = self.client.get(reverse("inventario:ingreso_nuevo")).content.decode()
        self.assertIn('id="modal-proveedor"', html)
        self.assertIn(f'action="{self.url}"', html)
        self.assertIn('name="proveedor-nombre"', html)
        self.assertIn("data-proveedor-rapido", html)
        # La ventanita es un formulario aparte, fuera del formulario del ingreso.
        self.assertLess(html.index("</form>"), html.index('id="form-proveedor-rapido"'))

    def test_registra_y_devuelve_el_proveedor(self):
        respuesta = self.client.post(self.url, {"proveedor-nombre": "  Proveedor   Taiwan ", "proveedor-ruc": "20123456789"})
        self.assertEqual(respuesta.status_code, 201)
        proveedor = Proveedor.objects.get()
        self.assertEqual(respuesta.json(), {"id": proveedor.pk, "nombre": "Proveedor Taiwan"})
        self.assertEqual(proveedor.tienda, self.tienda)

    def test_errores_en_json(self):
        Proveedor.objects.create(tienda=self.tienda, nombre="Importes SAC")
        respuesta = self.client.post(self.url, {"proveedor-nombre": "importes sac"})
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Ya tienes un proveedor con ese nombre.", respuesta.json()["errores"]["nombre"])
        self.assertEqual(self.client.post(self.url, {"proveedor-nombre": ""}).status_code, 400)

    def test_solo_post_y_solo_tiendas(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.client.logout()
        self.assertNotEqual(self.client.post(self.url, {"proveedor-nombre": "X"}).status_code, 201)
        self.assertFalse(Proveedor.objects.exists())


class FormulariosProtegidosTests(BaseInventario):
    def test_ingreso_y_venta_guardan_borrador_y_avisan(self):
        for nombre, clave in (("inventario:ingreso_nuevo", "ingreso"), ("inventario:venta_nueva", "venta")):
            html = self.client.get(reverse(nombre)).content.decode()
            self.assertIn(f'data-borrador="{clave}-u{self.tienda.usuario.pk}"', html)
            self.assertIn("data-avisar-salida", html)
            self.assertIn("data-lineas", html)
            self.assertIn("data-guardar-borrador>+ Crear producto</a>", html)
            self.assertIn("js/lineas_productos.js", html)
            self.assertIn("js/no_perder.js", html)

    def test_otros_formularios_largos_avisan_al_salir(self):
        for url in (reverse("catalogo:crear"), reverse("tiendas:editar"), reverse("inventario:ajuste_nuevo"),
                    reverse("inventario:conteo"), reverse("inventario:proveedor_crear")):
            self.assertContains(self.client.get(url), "data-avisar-salida", msg_prefix=url)
        self.assertContains(self.client.get(reverse("inventario:conteo")), "data-borrador-mezclar")

    def test_los_scripts(self):
        codigo = estatico("js/no_perder.js")
        for texto in ('window.addEventListener("beforeunload"', "localStorage", "DIAS = 3", "Recuperar", "Descartar",
                      '"borrador:restaurado"', "csrfmiddlewaretoken"):
            self.assertIn(texto, codigo)
        lineas = estatico("js/lineas_productos.js")
        self.assertIn("Ese producto ya estaba en la fila", lineas)
        self.assertIn('get("producto")', lineas)
        self.assertIn('select.addEventListener("change"', estatico("js/buscador_productos.js"))


class ProductoRepetidoTests(BaseInventario):
    def lineas(self, prefijo, filas):
        datos = {f"{prefijo}-TOTAL_FORMS": "10", f"{prefijo}-INITIAL_FORMS": "0",
                 f"{prefijo}-MIN_NUM_FORMS": "0", f"{prefijo}-MAX_NUM_FORMS": "10"}
        for n, fila in enumerate(filas):
            datos.update({f"{prefijo}-{n}-{campo}": valor for campo, valor in fila.items()})
        return datos

    def test_ingreso_rechaza_el_mismo_producto_en_dos_filas(self):
        fila = {"producto": self.producto.pk, "cantidad": "1", "costo": "3200"}
        respuesta = self.client.post(reverse("inventario:ingreso_nuevo"), self.lineas("lineas", [fila, fila]))
        self.assertContains(respuesta, "«Asus TUF A15» está en dos filas. Déjalo en una sola fila con la cantidad total.")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 4)

    def test_venta_rechaza_el_mismo_producto_en_dos_filas(self):
        fila = {"producto": self.producto.pk, "cantidad": "1"}
        datos = {**self.lineas("lineas", [fila, fila]), "metodo_pago": "efectivo"}
        respuesta = self.client.post(reverse("inventario:venta_nueva"), datos)
        self.assertContains(respuesta, "está en dos filas")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 4)
