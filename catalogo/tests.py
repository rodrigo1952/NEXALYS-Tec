"""
Pruebas del módulo principal: CRUD de productos (CU-03) y catálogo público (CU-04, CU-05).
Ejecutar con:  python manage.py test
"""

import io
import os
import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from tiendas.models import Tienda
from tiendas.tests import crear_tienda

from .models import Categoria, Marca, Producto

CARPETA_MEDIA_PRUEBAS = tempfile.mkdtemp()


def imagen_png(nombre="foto.png", ancho=50, alto=50, ruido=False):
    if ruido:
        imagen = Image.frombytes("RGB", (ancho, alto), os.urandom(ancho * alto * 3))
    else:
        imagen = Image.new("RGB", (ancho, alto), "blue")
    archivo = io.BytesIO()
    imagen.save(archivo, "PNG")
    return SimpleUploadedFile(nombre, archivo.getvalue(), content_type="image/png")


class BaseCatalogo(TestCase):
    def setUp(self):
        self.categoria, _ = Categoria.objects.get_or_create(nombre="Celulares")
        self.marca, _ = Marca.objects.get_or_create(nombre="Samsung")
        self.tienda = crear_tienda("tienda1", "Tienda Uno", "911111111")
        self.otra_tienda = crear_tienda("tienda2", "Tienda Dos", "922222222")

    def crear_producto(self, tienda=None, **datos):
        valores = {
            "tienda": tienda or self.tienda,
            "categoria": self.categoria,
            "marca": self.marca,
            "nombre": "Galaxy A15",
            "precio": Decimal("699.90"),
            "stock": 5,
        }
        valores.update(datos)
        return Producto.objects.create(**valores)

    def datos_formulario(self, **cambios):
        datos = {
            "nombre": "Galaxy A25",
            "categoria": self.categoria.pk,
            "marca": self.marca.pk,
            "precio": "899.00",
            "stock": "10",
            "descripcion": "128 GB",
            "activo": "on",
        }
        datos.update(cambios)
        return datos


@override_settings(MEDIA_ROOT=CARPETA_MEDIA_PRUEBAS)
class CrudProductoTests(BaseCatalogo):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CARPETA_MEDIA_PRUEBAS, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.client.force_login(self.tienda.usuario)

    # --- Crear ---------------------------------------------------------------
    def test_crear_producto_valido_queda_asociado_a_la_tienda(self):
        respuesta = self.client.post(reverse("catalogo:crear"), self.datos_formulario())
        self.assertRedirects(respuesta, reverse("catalogo:mis_productos"))
        producto = Producto.objects.get(nombre="Galaxy A25")
        self.assertEqual(producto.tienda, self.tienda)

    def test_precio_cero_se_rechaza(self):
        respuesta = self.client.post(reverse("catalogo:crear"), self.datos_formulario(precio="0"))
        self.assertIn("precio", respuesta.context["form"].errors)
        self.assertFalse(Producto.objects.exists())

    def test_stock_negativo_se_rechaza(self):
        respuesta = self.client.post(reverse("catalogo:crear"), self.datos_formulario(stock="-3"))
        self.assertIn("stock", respuesta.context["form"].errors)

    def test_campos_obligatorios(self):
        respuesta = self.client.post(reverse("catalogo:crear"), {})
        for campo in ["nombre", "categoria", "marca", "precio"]:
            self.assertIn(campo, respuesta.context["form"].errors)

    def test_nombre_repetido_en_la_misma_tienda_se_rechaza(self):
        self.crear_producto(nombre="Galaxy A25")
        respuesta = self.client.post(reverse("catalogo:crear"), self.datos_formulario(nombre="galaxy  a25"))
        self.assertIn("nombre", respuesta.context["form"].errors)

    def test_mismo_nombre_en_otra_tienda_si_se_permite(self):
        self.crear_producto(tienda=self.otra_tienda, nombre="Galaxy A25")
        self.client.post(reverse("catalogo:crear"), self.datos_formulario())
        self.assertEqual(Producto.objects.filter(nombre="Galaxy A25").count(), 2)

    def test_imagen_valida_se_guarda(self):
        self.client.post(reverse("catalogo:crear"), self.datos_formulario(imagen=imagen_png()))
        self.assertTrue(Producto.objects.get().imagen.name.startswith("productos/"))

    def test_archivo_que_no_es_imagen_se_rechaza(self):
        archivo = SimpleUploadedFile("virus.png", b"no soy una imagen", content_type="image/png")
        respuesta = self.client.post(reverse("catalogo:crear"), self.datos_formulario(imagen=archivo))
        self.assertIn("imagen", respuesta.context["form"].errors)

    def test_imagen_de_mas_de_2mb_se_rechaza(self):
        grande = imagen_png("grande.png", 1000, 1000, ruido=True)
        self.assertGreater(grande.size, 2 * 1024 * 1024)
        respuesta = self.client.post(reverse("catalogo:crear"), self.datos_formulario(imagen=grande))
        self.assertIn("imagen", respuesta.context["form"].errors)

    # --- Listar / Editar / Eliminar -----------------------------------------
    def test_listado_muestra_solo_productos_propios(self):
        self.crear_producto(nombre="Producto propio")
        self.crear_producto(tienda=self.otra_tienda, nombre="Producto ajeno")
        respuesta = self.client.get(reverse("catalogo:mis_productos"))
        self.assertContains(respuesta, "Producto propio")
        self.assertNotContains(respuesta, "Producto ajeno")

    def test_editar_producto_propio(self):
        producto = self.crear_producto()
        self.client.post(
            reverse("catalogo:editar", args=[producto.pk]),
            self.datos_formulario(nombre="Galaxy A15", precio="650.00", stock="2"),
        )
        producto.refresh_from_db()
        self.assertEqual(producto.precio, Decimal("650.00"))
        self.assertEqual(producto.stock, 2)

    def test_eliminar_producto_propio(self):
        producto = self.crear_producto()
        self.client.post(reverse("catalogo:eliminar", args=[producto.pk]))
        self.assertFalse(Producto.objects.filter(pk=producto.pk).exists())

    # --- Reglas de seguridad ---------------------------------------------------
    def test_no_puede_editar_producto_de_otra_tienda(self):
        ajeno = self.crear_producto(tienda=self.otra_tienda)
        respuesta = self.client.post(reverse("catalogo:editar", args=[ajeno.pk]), self.datos_formulario())
        self.assertEqual(respuesta.status_code, 404)

    def test_no_puede_eliminar_producto_de_otra_tienda(self):
        ajeno = self.crear_producto(tienda=self.otra_tienda)
        respuesta = self.client.post(reverse("catalogo:eliminar", args=[ajeno.pk]))
        self.assertEqual(respuesta.status_code, 404)
        self.assertTrue(Producto.objects.filter(pk=ajeno.pk).exists())

    def test_tienda_suspendida_no_puede_gestionar_productos(self):
        self.tienda.estado = Tienda.Estado.SUSPENDIDA
        self.tienda.save()
        respuesta = self.client.get(reverse("catalogo:mis_productos"))
        self.assertRedirects(respuesta, reverse("tiendas:panel"))


class AccesoPorRolTests(BaseCatalogo):
    def test_visitante_sin_sesion_es_enviado_al_login(self):
        respuesta = self.client.get(reverse("catalogo:mis_productos"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("login"), respuesta.url)

    def test_cliente_no_puede_entrar_a_mis_productos(self):
        cliente = User.objects.create_user("cliente1", "c@ejemplo.com", "ClaveSegura#2026")
        self.client.force_login(cliente)
        respuesta = self.client.get(reverse("catalogo:mis_productos"))
        self.assertEqual(respuesta.status_code, 403)


class CatalogoPublicoTests(BaseCatalogo):
    def test_catalogo_se_ve_sin_iniciar_sesion(self):
        self.crear_producto(nombre="Galaxy A15")
        respuesta = self.client.get(reverse("catalogo:catalogo"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Galaxy A15")

    def test_oculta_productos_no_publicados_y_de_tiendas_no_activas(self):
        self.crear_producto(nombre="Visible")
        self.crear_producto(nombre="Oculto por la tienda", activo=False)
        self.otra_tienda.estado = Tienda.Estado.SUSPENDIDA
        self.otra_tienda.save()
        self.crear_producto(tienda=self.otra_tienda, nombre="De tienda suspendida")
        respuesta = self.client.get(reverse("catalogo:catalogo"))
        self.assertContains(respuesta, "Visible")
        self.assertNotContains(respuesta, "Oculto por la tienda")
        self.assertNotContains(respuesta, "De tienda suspendida")

    def test_detalle_de_producto_oculto_responde_404(self):
        producto = self.crear_producto(activo=False)
        respuesta = self.client.get(reverse("catalogo:detalle", args=[producto.pk]))
        self.assertEqual(respuesta.status_code, 404)

    def test_buscar_por_texto(self):
        self.crear_producto(nombre="Galaxy A15")
        self.crear_producto(nombre="Audífonos inalámbricos")
        respuesta = self.client.get(reverse("catalogo:catalogo"), {"q": "galaxy"})
        self.assertContains(respuesta, "Galaxy A15")
        self.assertNotContains(respuesta, "Audífonos inalámbricos")

    def test_filtrar_por_rango_de_precio(self):
        self.crear_producto(nombre="Barato", precio=Decimal("50"))
        self.crear_producto(nombre="Caro", precio=Decimal("3000"))
        respuesta = self.client.get(reverse("catalogo:catalogo"), {"precio_min": "10", "precio_max": "100"})
        self.assertContains(respuesta, "Barato")
        self.assertNotContains(respuesta, "Caro")

    def test_precio_minimo_mayor_que_maximo_muestra_error(self):
        respuesta = self.client.get(reverse("catalogo:catalogo"), {"precio_min": "500", "precio_max": "100"})
        self.assertContains(respuesta, "no puede ser mayor que el precio máximo")

    def test_detalle_tiene_enlace_de_whatsapp_con_el_producto(self):
        producto = self.crear_producto(nombre="Galaxy A15")
        respuesta = self.client.get(reverse("catalogo:detalle", args=[producto.pk]))
        self.assertContains(respuesta, "https://wa.me/51911111111?text=")
        self.assertIn("Galaxy%20A15", producto.enlace_whatsapp())
