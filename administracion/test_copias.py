"""Copias de seguridad: base de datos + fotos en un .zip, 14 días en el servidor y descarga desde la consola."""
import os
import shutil
import sqlite3
import tempfile
import time
import zipfile
from io import StringIO
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase, override_settings
from django.urls import reverse

from catalogo.models import Categoria

from . import copias

CLAVE = "ClaveSegura#2026"


class BaseCopias(TransactionTestCase):
    # Sin transacción abierta, como en el servidor: SQLite no copia una base con una escritura a medias.
    # serialized_rollback: al terminar se devuelven los datos iniciales (roles, categorías) para las demás pruebas.
    serialized_rollback = True

    def setUp(self):
        self.media = Path(tempfile.mkdtemp())
        self.carpeta = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.media, True)
        self.addCleanup(shutil.rmtree, self.carpeta, True)
        ajustes = override_settings(MEDIA_ROOT=str(self.media), COPIAS_CARPETA=str(self.carpeta))
        ajustes.enable()
        self.addCleanup(ajustes.disable)
        (self.media / "tiendas" / "1-kantu").mkdir(parents=True)
        (self.media / "tiendas" / "1-kantu" / "foto.webp").write_bytes(b"FOTO")
        (self.media / "miniaturas" / "tarjeta").mkdir(parents=True)
        (self.media / "miniaturas" / "tarjeta" / "foto.webp").write_bytes(b"MINI")


class CrearCopiaTests(BaseCopias):
    def test_copia_con_base_de_datos_y_fotos_sin_miniaturas(self):
        Categoria.objects.create(nombre="Drones")
        copia = copias.crear()
        self.assertRegex(copia["nombre"], r"^nexalys-copia-\d{8}-\d{6}\.zip$")
        with zipfile.ZipFile(copia["ruta"]) as archivo:
            nombres = archivo.namelist()
            self.assertIn("LEEME.txt", nombres)
            self.assertIn("media/tiendas/1-kantu/foto.webp", nombres)
            self.assertNotIn("media/miniaturas/tarjeta/foto.webp", nombres)
            base = Path(tempfile.mkdtemp()) / "db.sqlite3"
            base.write_bytes(archivo.read("db.sqlite3"))
        with sqlite3.connect(base) as conexion:
            nombres_cat = [fila[0] for fila in conexion.execute("SELECT nombre FROM catalogo_categoria")]
        self.assertIn("Drones", nombres_cat)  # la copia tiene los datos de ese momento

    def test_se_borran_las_de_mas_de_14_dias_pero_nunca_la_ultima(self):
        vieja = self.carpeta / "nexalys-copia-20260101-030000.zip"
        vieja.write_bytes(b"x")
        hace_20_dias = time.time() - 20 * 86400
        os.utime(vieja, (hace_20_dias, hace_20_dias))
        reciente = self.carpeta / "nexalys-copia-20260102-030000.zip"
        reciente.write_bytes(b"x")
        copias.crear()
        self.assertFalse(vieja.exists())
        self.assertTrue(reciente.exists())
        sola = self.carpeta / "nexalys-copia-20250101-030000.zip"
        for archivo in self.carpeta.iterdir():
            archivo.unlink()
        sola.write_bytes(b"x")
        os.utime(sola, (hace_20_dias, hace_20_dias))
        copias.borrar_viejas()
        self.assertTrue(sola.exists())  # es la única: no se borra

    def test_comando_diario(self):
        salida = StringIO()
        call_command("copia_seguridad", stdout=salida)
        self.assertIn("Listo: nexalys-copia-", salida.getvalue())
        self.assertEqual(len(copias.listar()), 1)

    def test_restaurar_pide_confirmar(self):
        with self.assertRaisesMessage(CommandError, "--confirmar"):
            call_command("restaurar_copia", "algo.zip")

    def test_restaurar_rechaza_un_zip_que_no_es_copia(self):
        falso = self.carpeta / "otro.zip"
        with zipfile.ZipFile(falso, "w") as archivo:
            archivo.writestr("hola.txt", "hola")
        with self.assertRaisesMessage(CommandError, "no es una copia"):
            call_command("restaurar_copia", str(falso), "--confirmar")


class ConsolaCopiasTests(BaseCopias):
    def setUp(self):
        super().setUp()
        self.client.force_login(User.objects.create_superuser("jefe", "j@ejemplo.com", CLAVE))

    def test_crear_listar_y_descargar(self):
        respuesta = self.client.get(reverse("administracion:copias"))
        self.assertContains(respuesta, "No hay una copia de los últimos 2 días.")
        respuesta = self.client.post(reverse("administracion:copias_crear"), follow=True)
        self.assertContains(respuesta, "Copia creada: nexalys-copia-")
        self.assertContains(respuesta, "la más reciente")
        self.assertNotContains(respuesta, "No hay una copia de los últimos 2 días.")
        nombre = copias.listar()[0]["nombre"]
        descarga = self.client.get(reverse("administracion:copias_descargar", args=[nombre]))
        self.assertEqual(descarga["Content-Type"], "application/zip")
        self.assertIn(f'filename="{nombre}"', descarga["Content-Disposition"])
        self.assertTrue(zipfile.is_zipfile(__import__("io").BytesIO(b"".join(descarga.streaming_content))))

    def test_no_se_puede_pedir_otro_archivo(self):
        for nombre in ("db.sqlite3", "..%2F.env", "nexalys-copia-20260101-030000.zip"):
            self.assertEqual(self.client.get(f"/administracion/copias/{nombre}/").status_code, 404, nombre)

    def test_solo_el_administrador(self):
        cliente = User.objects.create_user("cli", "c@ejemplo.com", CLAVE)
        self.client.force_login(cliente)
        self.assertEqual(self.client.get(reverse("administracion:copias")).status_code, 403)
        self.assertEqual(self.client.post(reverse("administracion:copias_crear")).status_code, 403)
