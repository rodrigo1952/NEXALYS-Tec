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


def correr_como_servidor(*argumentos, **variables):
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


class AjustesTests(SimpleTestCase):
    def test_la_clave_secreta_no_esta_en_el_codigo(self):
        codigo = (RAIZ / "config" / "settings.py").read_text(encoding="utf-8")
        self.assertNotIn("django-insecure", codigo)
        self.assertNotIn(settings.SECRET_KEY, codigo)

    def test_env_en_gitignore_y_modelo_sin_secretos(self):
        self.assertIn(".env", (RAIZ / ".gitignore").read_text(encoding="utf-8").split())
        modelo = (RAIZ / ".env.example").read_text(encoding="utf-8")
        self.assertIn("SECRET_KEY=\n", modelo)

    correr = staticmethod(lambda *a, **v: correr_como_servidor(*a, **v))

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


MANIFIESTO = {
    "default": settings.STORAGES["default"],
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"},
}


class ServidorListoTests(SimpleTestCase):
    def test_collectstatic_con_huella(self):
        """Como en el servidor: junta los archivos y les pone una huella al nombre."""
        from django.core.management import call_command
        from django.templatetags.static import static
        from django.test import override_settings

        with tempfile.TemporaryDirectory() as carpeta, override_settings(STATIC_ROOT=carpeta, STORAGES=MANIFIESTO):
            call_command("collectstatic", interactive=False, verbosity=0)
            self.assertTrue((Path(carpeta) / "staticfiles.json").exists())
            for archivo in ("css/marca.css", "js/whatsapp.js", "js/compartir.js", "img/favicon.svg",
                            "vendor/bootstrap/bootstrap.min.css", "vendor/leaflet/leaflet.css", "vendor/fuentes/fuentes.css"):
                url = static(archivo)
                nombre = Path(archivo).stem
                self.assertRegex(url, rf"/static/.*{nombre}\.[0-9a-f]{{12}}\.", archivo)
                self.assertTrue((Path(carpeta) / url.removeprefix("/static/")).exists(), url)

    def test_en_el_servidor_usa_huellas(self):
        resultado = correr_como_servidor(
            "shell", "-c", "from django.conf import settings; print(settings.STORAGES['staticfiles']['BACKEND'])"
        )
        self.assertIn("ManifestStaticFilesStorage", resultado.stdout)

    def test_sin_numeros_v_a_mano(self):
        for plantilla in (RAIZ / "templates").rglob("*.html"):
            self.assertNotIn("%}?v=", plantilla.read_text(encoding="utf-8"), plantilla.name)

    def test_versiones_fijas(self):
        lineas = (RAIZ / "requirements.txt").read_text(encoding="utf-8").split()
        self.assertTrue(lineas)
        for linea in lineas:
            self.assertRegex(linea, r"^[A-Za-z0-9_.-]+==[0-9][0-9A-Za-z.]*$", linea)

    def test_staticfiles_fuera_de_git(self):
        self.assertIn("staticfiles/", (RAIZ / ".gitignore").read_text(encoding="utf-8").split())


class CabeceraCspTests(TestCase):
    def test_cabecera_con_nonce_en_cada_script_en_linea(self):
        import re

        for url in (reverse("inicio"), reverse("catalogo:catalogo"), reverse("login")):
            respuesta = self.client.get(url)
            politica = respuesta["Content-Security-Policy"]
            nonce = re.search(r"'nonce-([^']+)'", politica).group(1)
            self.assertIn("object-src 'none'", politica)
            self.assertIn("frame-ancestors 'none'", politica)
            html = respuesta.content.decode()
            scripts = re.findall(r"<script(?![^>]*\bsrc=)(?![^>]*application/json)([^>]*)>", html)
            self.assertTrue(scripts, url)
            for atributos in scripts:
                self.assertIn(f'nonce="{nonce}"', atributos, url)

    def test_cada_visita_tiene_otro_nonce(self):
        primera = self.client.get(reverse("inicio"))["Content-Security-Policy"]
        segunda = self.client.get(reverse("inicio"))["Content-Security-Policy"]
        self.assertNotEqual(primera, segunda)

    def test_scripts_solo_de_la_pagina_y_librerias_con_version(self):
        politica = self.client.get(reverse("inicio"))["Content-Security-Policy"]
        directiva = next(d for d in politica.split(";") if d.strip().startswith("script-src"))
        self.assertNotIn("unsafe-inline", directiva)
        self.assertNotIn("unsafe-eval", directiva)
        self.assertRegex(directiva.strip(), r"^script-src 'self' 'nonce-[^']+'$")  # nada de otros sitios

    def test_plantillas_sin_onclick_ni_scripts_sin_nonce(self):
        import re

        for plantilla in (RAIZ / "templates").rglob("*.html"):
            texto = plantilla.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"\son(click|change|submit|load|input)=", texto), plantilla.name)
            self.assertNotIn("<script>", texto, plantilla.name)


class PlantillasTests(SimpleTestCase):
    def test_comentarios_de_una_sola_linea(self):
        """{# … #} solo sirve en una línea: si se parte en dos, el texto aparece en la página."""
        import re

        for plantilla in (RAIZ / "templates").rglob("*.html"):
            for numero, linea in enumerate(plantilla.read_text(encoding="utf-8").splitlines(), 1):
                sin_cerrar = re.sub(r"\{#.*?#\}", "", linea)
                self.assertNotIn("{#", sin_cerrar, f"{plantilla.name}, línea {numero}")


class CorreoRealTests(SimpleTestCase):
    def test_con_servidor_en_el_env_usa_smtp(self):
        resultado = correr_como_servidor(
            "shell", "-c",
            "from django.conf import settings; m = settings.MAILERS['default']; "
            "print(m['BACKEND'], m['OPTIONS']['host'], m['OPTIONS']['port'], m['OPTIONS']['use_tls']); "
            "print(settings.DEFAULT_FROM_EMAIL)",
            CORREO_SERVIDOR="smtp.gmail.com", CORREO_USUARIO="nexalys@gmail.com", CORREO_CLAVE="abcd efgh ijkl mnop",
            CORREO_REMITENTE="NEXALYS Tec <nexalys@gmail.com>",
        )
        self.assertIn("django.core.mail.backends.smtp.EmailBackend smtp.gmail.com 587 True", resultado.stdout)
        self.assertIn("NEXALYS Tec <nexalys@gmail.com>", resultado.stdout)

    def test_sin_servidor_usa_la_terminal(self):
        resultado = correr_como_servidor(
            "shell", "-c", "from django.conf import settings; print(settings.MAILERS['default']['BACKEND'])",
            CORREO_SERVIDOR="",
        )
        self.assertIn("console.EmailBackend", resultado.stdout)

    def test_check_deploy_sin_errores_con_correo_real(self):
        resultado = correr_como_servidor(
            "check", "--deploy", CORREO_SERVIDOR="smtp.gmail.com", CORREO_USUARIO="a@gmail.com", CORREO_CLAVE="x",
        )
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertNotIn("mail.E001", resultado.stdout + resultado.stderr)

    def test_comando_probar_correo(self):
        from io import StringIO

        from django.core import mail
        from django.core.management import call_command

        salida = StringIO()
        call_command("probar_correo", "ana@ejemplo.com", stdout=salida)
        self.assertIn("Listo: se envió el correo de prueba a ana@ejemplo.com.", salida.getvalue())
        self.assertEqual(mail.outbox[-1].to, ["ana@ejemplo.com"])


class LibreriasPropiasTests(SimpleTestCase):
    """Bootstrap, íconos, Chart.js, Leaflet y las letras están en static/vendor: nada se pide a un CDN."""

    VENDOR = RAIZ / "static" / "vendor"

    def test_ninguna_plantilla_usa_un_cdn(self):
        import re

        for plantilla in (RAIZ / "templates").rglob("*.html"):
            texto = plantilla.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"cdn\.jsdelivr|cdnjs|fonts\.googleapis|fonts\.gstatic", texto), plantilla.name)

    def test_estan_las_librerias_con_su_version_y_licencia(self):
        versiones = {
            "bootstrap/bootstrap.min.css": "Bootstrap  v5.3.3", "bootstrap/bootstrap.bundle.min.js": "Bootstrap v5.3.3",
            "bootstrap-icons/bootstrap-icons.min.css": "Bootstrap Icons v1.11.3", "chartjs/chart.umd.js": "Chart.js v4.4.1",
            "leaflet/leaflet.js": "Leaflet 1.9.4",
        }
        for archivo, version in versiones.items():
            texto = (self.VENDOR / archivo).read_text(encoding="utf-8")
            self.assertIn(version, texto[:400], archivo)
            self.assertNotIn("sourceMappingURL", texto, archivo)
        for licencia in ("bootstrap/LICENSE", "bootstrap-icons/LICENSE", "chartjs/LICENSE.md", "leaflet/LICENSE",
                         "fuentes/LICENSE-space-grotesk", "fuentes/LICENSE-lilita-one"):
            self.assertTrue((self.VENDOR / licencia).exists(), licencia)
        for letra in ("space-grotesk-latin", "space-grotesk-latin-ext", "lilita-one-latin", "lilita-one-latin-ext"):
            self.assertEqual((self.VENDOR / "fuentes" / f"{letra}.woff2").read_bytes()[:4], b"wOF2", letra)


class EstaticosEnTuPCTests(TestCase):
    """Con DEBUG=True, los CSS y JS llevan ?v=<fecha del archivo>: el navegador no usa copias viejas."""

    def test_el_enlace_lleva_la_fecha_del_archivo(self):
        import os

        from django.contrib.staticfiles import finders

        from config.estaticos import EstaticosConVersion

        almacen = EstaticosConVersion()
        fecha = int(os.path.getmtime(finders.find("js/compartir.js")))
        self.assertEqual(almacen.url("js/compartir.js"), f"/static/js/compartir.js?v={fecha}")
        self.assertEqual(almacen.url("no-existe.js"), "/static/no-existe.js")

    def test_settings_lo_usa_solo_en_tu_pc(self):
        texto = (RAIZ / "config" / "settings.py").read_text(encoding="utf-8")
        self.assertIn("'config.estaticos.EstaticosConVersion' if DEBUG", texto)

