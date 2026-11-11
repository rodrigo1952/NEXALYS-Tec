"""Producción segura: datos secretos en el .env, ajustes de HTTPS y Django Admin en una dirección secreta."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from . import crear_env, entorno

RAIZ = Path(settings.BASE_DIR)


class ArchivoEnvTests(SimpleTestCase):
    def leer(self, texto, existentes=None):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / ".env"
            ruta.write_text(texto, encoding="utf-8")
            with mock.patch.dict(os.environ, existentes or {}, clear=True):
                entorno.cargar_env(ruta)
                return dict(os.environ)

    def test_lee_datos_comentarios_y_comillas(self):
        datos = self.leer('# comentario\n\nDEBUG=True\nSITIO_URL="https://a.com"\nCLAVE=a=b#c\n')
        self.assertEqual(datos, {"DEBUG": "True", "SITIO_URL": "https://a.com", "CLAVE": "a=b#c"})

    def test_no_pisa_las_variables_del_sistema(self):
        self.assertEqual(self.leer("DEBUG=True\n", {"DEBUG": "False"})["DEBUG"], "False")

    def test_sin_archivo_no_falla(self):
        entorno.cargar_env(Path(tempfile.gettempdir()) / "no-existe" / ".env")

    def test_si_o_no_y_listas(self):
        with mock.patch.dict(os.environ, {"A": "Sí", "B": "false", "L": "a.com, b.com,"}, clear=True):
            self.assertTrue(entorno.si_o_no("A"))
            self.assertFalse(entorno.si_o_no("B", True))
            self.assertTrue(entorno.si_o_no("FALTA", True))
            self.assertEqual(entorno.lista("L"), ["a.com", "b.com"])
            self.assertEqual(entorno.lista("FALTA", ["x"]), ["x"])


class CrearEnvTests(SimpleTestCase):
    def datos(self, texto):
        return dict(linea.split("=", 1) for linea in texto.splitlines() if linea and not linea.startswith("#"))

    def test_para_la_pc(self):
        datos = self.datos(crear_env.contenido())
        self.assertEqual(len(datos["SECRET_KEY"]), 50)
        self.assertEqual(datos["DEBUG"], "True")
        self.assertRegex(datos["DJANGO_ADMIN_URL"], r"^control-[a-z0-9]{12}/$")

    def test_para_el_servidor(self):
        datos = self.datos(crear_env.contenido(produccion=True))
        self.assertEqual(datos["DEBUG"], "False")
        self.assertEqual(datos["IP_CABECERA"], "HTTP_X_REAL_IP")
        self.assertTrue(datos["SITIO_URL"].startswith("https://"))

    def test_cada_vez_una_clave_distinta(self):
        self.assertNotEqual(crear_env.clave_secreta(), crear_env.clave_secreta())

    def test_no_reemplaza_un_env_existente(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / ".env"
            ruta.write_text("SECRET_KEY=mia\n", encoding="utf-8")
            with mock.patch.object(crear_env, "ARCHIVO", ruta), mock.patch("builtins.print"):
                self.assertEqual(crear_env.main(), 1)
            self.assertEqual(ruta.read_text(encoding="utf-8"), "SECRET_KEY=mia\n")


class AjustesTests(SimpleTestCase):
    def test_la_clave_secreta_no_esta_en_el_codigo(self):
        codigo = (RAIZ / "config" / "settings.py").read_text(encoding="utf-8")
        self.assertNotIn("django-insecure", codigo)
        self.assertNotIn(settings.SECRET_KEY, codigo)

    def test_env_en_gitignore_y_modelo_sin_secretos(self):
        self.assertIn(".env", (RAIZ / ".gitignore").read_text(encoding="utf-8").split())
        modelo = (RAIZ / ".env.example").read_text(encoding="utf-8")
        self.assertIn("SECRET_KEY=\n", modelo)

    def correr(self, *argumentos, **variables):
        """Arranca Django como en el servidor (sin leer tu .env: las variables del sistema ganan)."""
        entorno_servidor = {
            **os.environ, "DEBUG": "False", "SECRET_KEY": crear_env.clave_secreta(), "ALLOWED_HOSTS": "nexalys.pythonanywhere.com",
            "SITIO_URL": "https://nexalys.pythonanywhere.com", "DJANGO_ADMIN_URL": "control-prueba/",
            **variables,
        }
        return subprocess.run(
            [sys.executable, "manage.py", *argumentos], cwd=RAIZ, env=entorno_servidor,
            capture_output=True, text=True, timeout=120,
        )

    def test_check_deploy_sin_avisos_de_seguridad(self):
        resultado = self.correr("check", "--deploy")
        salida = resultado.stdout + resultado.stderr
        self.assertNotIn("security.", salida)

    def test_sin_clave_secreta_no_arranca(self):
        resultado = self.correr("check", SECRET_KEY="")
        self.assertNotEqual(resultado.returncode, 0)
        self.assertIn("Falta SECRET_KEY", resultado.stderr)

    def test_sin_debug_en_el_env_se_asume_false(self):
        variables = {k: v for k, v in os.environ.items() if k != "DEBUG"}
        with mock.patch.dict(os.environ, variables, clear=True):
            self.assertFalse(entorno.si_o_no("DEBUG", False))


class AdminSecretoTests(TestCase):
    def test_admin_en_la_direccion_del_env(self):
        self.assertEqual(reverse("admin:index"), f"/{settings.ADMIN_URL}")

    def test_la_direccion_conocida_no_existe(self):
        if settings.ADMIN_URL == "admin/":
            self.skipTest("Este .env no tiene DJANGO_ADMIN_URL")
        self.assertEqual(self.client.get("/admin/").status_code, 404)

    def test_el_admin_usa_el_inicio_de_sesion_de_la_pagina(self):
        respuesta = self.client.get(reverse("admin:index"))
        respuesta = self.client.get(respuesta["Location"])
        self.assertRedirects(
            respuesta, f"{reverse('login')}?next=/{settings.ADMIN_URL}", fetch_redirect_response=False
        )

    def test_el_superusuario_entra_al_admin(self):
        User.objects.create_superuser("jefe", "j@ejemplo.com", "ClaveSegura#2026")
        self.client.post(reverse("login"), {"username": "jefe", "password": "ClaveSegura#2026"})
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)
