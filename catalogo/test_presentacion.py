"""Productos de presentación: 3 tiendas de demostración con productos reales."""

import io
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from inventario.models import FichaInventario, Movimiento
from inventario.reportes import filtro_stock_bajo
from tiendas.models import Tienda
from tiendas.tests import crear_tienda

from . import presentacion
from .demo import CLAVE_DEMO
from .models import Categoria, Marca, Producto

NOMBRES = [t["nombre"] for t in presentacion.TIENDAS]


def cargar():
    salida = io.StringIO()
    call_command("cargar_productos_presentacion", stdout=salida)
    return salida.getvalue()


class PresentacionTests(TestCase):
    def test_crea_tres_tiendas_activas_con_horario_y_cuenta(self):
        salida = cargar()
        for datos in presentacion.TIENDAS:
            tienda = Tienda.objects.get(nombre=datos["nombre"])
            self.assertEqual(tienda.estado, Tienda.Estado.ACTIVA)
            self.assertIsNotNone(tienda.verificada_en)
            self.assertEqual(tienda.whatsapp, datos["whatsapp"])
            self.assertEqual(tienda.horarios.count(), 7)
            self.assertTrue(tienda.usuario.groups.filter(name="Tienda").exists())
            self.assertTrue(self.client.login(username=datos["usuario"], password=CLAVE_DEMO))
            self.client.logout()
        self.assertIn(CLAVE_DEMO, salida)

    def test_carga_todos_los_productos_visibles_en_el_catalogo(self):
        cargar()
        self.assertEqual(Producto.objects.filter(tienda__nombre__in=NOMBRES).count(), len(presentacion.PRODUCTOS))
        self.assertEqual(Producto.objects.visibles().count(), len(presentacion.PRODUCTOS))

    def test_reusa_categorias_y_marcas_sin_importar_mayusculas(self):
        Marca.objects.filter(nombre__iexact="Teros").delete()
        teros = Marca.objects.create(nombre="TEROS")
        cargar()
        self.assertEqual(Marca.objects.filter(nombre__iexact="teros").count(), 1)
        self.assertTrue(Producto.objects.filter(marca=teros).exists())
        categorias, marcas = Categoria.objects.count(), Marca.objects.count()
        cargar()
        self.assertEqual((Categoria.objects.count(), Marca.objects.count()), (categorias, marcas))

    def test_cada_tienda_tiene_alertas_destacados_y_ofertas(self):
        cargar()
        for nombre in NOMBRES:
            productos = Producto.objects.filter(tienda__nombre=nombre)
            with self.subTest(tienda=nombre):
                self.assertEqual(productos.filter(ficha__costo__isnull=True).count(), 3)
                self.assertEqual(productos.filter(filtro_stock_bajo()).count(), 3)
                self.assertEqual(productos.filter(stock=0).count(), 1)
                self.assertEqual(productos.filter(destacado=True).count(), 3)
                self.assertGreaterEqual(productos.en_oferta().count(), 2)

    def test_costo_entre_70_y_80_por_ciento_del_precio_final(self):
        cargar()
        for ficha in FichaInventario.objects.filter(costo__isnull=False).select_related("producto"):
            proporcion = ficha.costo / ficha.producto.precio_final
            with self.subTest(producto=ficha.producto.nombre):
                self.assertGreaterEqual(proporcion, Decimal("0.69"))
                self.assertLessEqual(proporcion, Decimal("0.81"))

    def test_el_stock_inicial_queda_en_el_kardex(self):
        cargar()
        producto = Producto.objects.get(nombre="Samsung Galaxy A26 5G 128GB 6GB RAM Negro")
        movimiento = Movimiento.objects.get(producto=producto)
        self.assertEqual(movimiento.tipo, Movimiento.Tipo.INICIAL)
        self.assertEqual(movimiento.cantidad, producto.stock)
        self.assertEqual(movimiento.usuario, producto.tienda.usuario)

    def test_cargar_dos_veces_no_duplica(self):
        cargar()
        salida = cargar()
        self.assertEqual(Producto.objects.filter(tienda__nombre__in=NOMBRES).count(), len(presentacion.PRODUCTOS))
        self.assertEqual(Tienda.objects.filter(nombre__in=NOMBRES).count(), 3)
        self.assertIn("ya existían", salida)

    def test_mueve_el_monitor_acer_a_pantallas(self):
        tienda = crear_tienda("tienda1", "Tienda Uno", "911111111")
        monitor = Producto.objects.create(
            tienda=tienda, categoria=Categoria.objects.get_or_create(nombre="Accesorios")[0],
            marca=Marca.objects.get_or_create(nombre="Acer")[0], nombre='Monitor Acer KA242Y ABI 23.8" Full HD',
            precio=Decimal("319"), stock=5,
        )
        salida = cargar()
        monitor.refresh_from_db()
        self.assertEqual(monitor.categoria.nombre, "Pantallas")
        self.assertIn("pantallas", monitor.etiquetas_busqueda)
        self.assertIn("Monitor Acer", salida)

    def test_whatsapp_ocupado_omite_esa_tienda_con_aviso(self):
        crear_tienda("otra", "Otra Tienda", presentacion.TIENDAS[0]["whatsapp"])
        salida = cargar()
        self.assertFalse(Tienda.objects.filter(nombre=presentacion.TIENDAS[0]["nombre"]).exists())
        self.assertFalse(User.objects.filter(username=presentacion.TIENDAS[0]["usuario"]).exists())
        self.assertTrue(Tienda.objects.filter(nombre=presentacion.TIENDAS[1]["nombre"]).exists())
        self.assertIn("ya lo usa", salida)

    def test_enlaces_para_las_fotos(self):
        texto = presentacion.enlaces_markdown()
        for dato in presentacion.PRODUCTOS:
            self.assertIn(dato["enlace"], texto)
