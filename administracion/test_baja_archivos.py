"""
Nov 2026: al eliminar una tienda o un producto, se elimine por donde se elimine (consola, limpieza
automática, Django Admin o en cascada), no quedan fotos, logos, miniaturas ni carpetas vacías,
y las ventas de la tienda se conservan anónimas (tiendas/baja.py). Comando limpiar_archivos.
"""

import io
import os
import shutil
import tempfile

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.test import override_settings

from catalogo.archivos import carpeta_tienda
from catalogo.imagenes import ruta_miniatura, url_miniatura
from catalogo.models import FotoProducto, Producto
from catalogo.test_carpetas import png
from catalogo.tests import BaseCatalogo
from inventario import servicios
from inventario.models import Movimiento, Venta
from tiendas.baja import carpetas_de

CARPETA_MEDIA = tempfile.mkdtemp()


def existe(relativa):
    return os.path.exists(os.path.join(settings.MEDIA_ROOT, relativa))


@override_settings(MEDIA_ROOT=CARPETA_MEDIA)
class ArchivosAlEliminarTests(BaseCatalogo):
    def setUp(self):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().setUp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def tienda_con_archivos(self):
        self.tienda.logo = png("logo.png")
        self.tienda.save()
        producto = self.crear_producto(nombre="Galaxy A15", imagen=png())
        FotoProducto.objects.create(producto=producto, imagen=png(), orden=1)
        url_miniatura(producto.imagen)
        url_miniatura(producto.imagen, "icono")
        url_miniatura(self.tienda.logo, "compartir")
        return producto

    def test_en_cascada_como_en_django_admin_no_queda_nada(self):
        self.tienda_con_archivos()
        carpetas = carpetas_de(self.tienda)
        for carpeta in carpetas:
            self.assertTrue(existe(carpeta), carpeta)
        with self.captureOnCommitCallbacks(execute=True):
            self.tienda.usuario.delete()  # cuenta → tienda → productos → fotos, sin pasar por la consola
        for carpeta in carpetas:
            self.assertFalse(existe(carpeta), carpeta)

    def test_borrar_productos_en_lote_borra_su_foto_y_miniaturas(self):
        producto = self.tienda_con_archivos()
        rutas = [producto.imagen.name, ruta_miniatura(producto.imagen.name, "tarjeta"),
                 ruta_miniatura(producto.imagen.name, "icono")]
        with self.captureOnCommitCallbacks(execute=True):
            Producto.objects.filter(pk=producto.pk).delete()  # como «Eliminar seleccionados» de Django Admin
        for ruta in rutas:
            self.assertFalse(existe(ruta), ruta)
        self.assertTrue(existe(self.tienda.logo.name))  # lo de la tienda sigue

    def test_ventas_quedan_anonimas_aunque_se_borre_solo_la_tienda(self):
        producto = self.crear_producto(nombre="Galaxy A15", stock=5)
        venta = servicios.registrar_venta(self.tienda, self.tienda.usuario,
                                          [servicios.LineaPedida(producto.pk, 1)], cliente_nombre="Ana Quispe")
        self.tienda.delete()  # como borrar la tienda en Django Admin
        venta.refresh_from_db()
        self.assertEqual((venta.tienda, venta.tienda_nombre, venta.cliente_nombre, venta.usuario),
                         (None, "Tienda eliminada", "Cliente anónimo", None))
        self.assertFalse(Movimiento.objects.filter(venta=venta).exists())  # el kardex era privado de la tienda
        self.assertEqual(Venta.objects.count(), 1)

    def test_comando_limpiar_archivos(self):
        producto = self.tienda_con_archivos()
        suelto = default_storage.save(f"{carpeta_tienda(self.tienda)}/productos/viejo.webp", ContentFile(b"x"))
        mini_suelta = default_storage.save("miniaturas/tarjeta/tiendas/99-cerrada/productos/a.webp", ContentFile(b"x"))

        salida = io.StringIO()
        call_command("limpiar_archivos", stdout=salida)  # vista previa: no borra nada
        self.assertIn("Archivos sueltos: 2", salida.getvalue())
        self.assertTrue(existe(suelto) and existe(mini_suelta))

        call_command("limpiar_archivos", "--borrar", stdout=io.StringIO())
        self.assertFalse(existe(suelto))
        self.assertFalse(existe("miniaturas/tarjeta/tiendas/99-cerrada"))  # su carpeta vacía también
        self.assertTrue(existe(producto.imagen.name))
        self.assertTrue(existe(ruta_miniatura(producto.imagen.name, "tarjeta")))
        self.assertTrue(existe(self.tienda.logo.name))

        salida = io.StringIO()
        call_command("limpiar_archivos", stdout=salida)
        self.assertIn("No hay archivos sueltos", salida.getvalue())
