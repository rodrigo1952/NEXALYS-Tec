"""
Correos con diseño profesional (config/correos.py): botón, enlace de respaldo, código de 6 dígitos,
bienvenida, «Responder» a soporte, línea de vista previa y vencimiento con fecha y hora.
"""

import io
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from config import correos
from cuentas.models import CodigoVerificacion
from tiendas.models import Tienda
from tiendas.tests import DATOS_VALIDOS as DATOS_TIENDA

LIMA = ZoneInfo("America/Lima")
SITIO = "https://prueba-nexalys.trycloudflare.com"
CLAVE = "ClaveSegura#2026"
DATOS_CLIENTE = {
    "username": "david_laura", "first_name": "David", "last_name": "Laura",
    "email": "david@ejemplo.com", "password1": CLAVE, "password2": CLAVE, "acepto_privacidad": "on",
}


def html_de(correo):
    return next(contenido for contenido, tipo in correo.alternatives if tipo == "text/html")


def codigo_de(correo):
    encontrado = re.search(r"código en [^:]+: (\d{3}) (\d{3})", correo.body)
    return encontrado.group(1) + encontrado.group(2)


class AyudantesTests(TestCase):
    def test_fecha_y_hora_en_palabras(self):
        casos = {
            datetime(2026, 11, 16, 17, 24, tzinfo=LIMA): "el lunes 16 de noviembre a las 5:24 p. m.",
            datetime(2026, 11, 17, 13, 5, tzinfo=LIMA): "el martes 17 de noviembre a la 1:05 p. m.",
            datetime(2026, 12, 6, 0, 30, tzinfo=LIMA): "el domingo 6 de diciembre a las 12:30 a. m.",
            datetime(2026, 1, 1, 12, 0, tzinfo=LIMA): "el jueves 1 de enero a las 12:00 p. m.",
        }
        for momento, esperado in casos.items():
            self.assertEqual(correos.fecha_en_palabras(momento), esperado)

    @override_settings(SITIO_URL=SITIO + "/")
    def test_los_enlaces_usan_sitio_url(self):
        self.assertEqual(correos.enlace("/catalogo/"), SITIO + "/catalogo/")

    @override_settings(CORREO_RESPUESTAS="soporte@ejemplo.com")
    def test_dos_versiones_vista_previa_y_responder_a_soporte(self):
        correos.enviar(["a@ejemplo.com"], "Prueba", "correos/prueba", vista_previa="Texto de vista previa")
        correo = mail.outbox[0]
        self.assertEqual(correo.reply_to, ["soporte@ejemplo.com"])
        self.assertIn("El correo funciona", correo.body)
        html = html_de(correo)
        self.assertIn("Texto de vista previa", html)
        self.assertIn("NEXALYS <span", html)
        self.assertIn("mailto:soporte@ejemplo.com", html)

    @override_settings(CORREO_RESPUESTAS="")
    def test_sin_correo_de_soporte_no_hay_responder_a(self):
        correos.enviar(["a@ejemplo.com"], "Prueba", "correos/prueba")
        self.assertEqual(mail.outbox[0].reply_to, [])

    def test_probar_correo_usa_el_diseno(self):
        call_command("probar_correo", "a@ejemplo.com", stdout=io.StringIO())
        self.assertEqual(mail.outbox[0].subject, "Prueba de correo | NEXALYS Tec")
        self.assertIn("El correo funciona", html_de(mail.outbox[0]))


@override_settings(SITIO_URL=SITIO)
class ConfirmacionClienteTests(TestCase):
    def registrar(self):
        return self.client.post(reverse("registro"), DATOS_CLIENTE)

    def test_correo_profesional_con_boton_codigo_y_vencimiento(self):
        self.registrar()
        correo = mail.outbox[0]
        html = html_de(correo)
        self.assertIn(">Confirmar mi correo</a>", html)
        self.assertIn(f'href="{SITIO}/registro/confirmar/', html)  # https desde SITIO_URL
        self.assertIn("¿El botón no funciona?", html)  # enlace de respaldo pequeño
        self.assertIn("Hola, David:", html)
        codigo = codigo_de(correo)
        self.assertIn(f"{codigo[:3]} {codigo[3:]}", html)
        self.assertIn(f"Activa tu cuenta con un toque o con el código {codigo[:3]} {codigo[3:]}.", html)
        self.assertRegex(html, r"funcionan hasta <strong>el \w+ \d+ de \w+ a las? \d+:\d\d [ap]\. m\.</strong>")
        self.assertNotIn(codigo, CodigoVerificacion.objects.get().huella)  # solo se guarda la huella

    def test_el_codigo_activa_la_cuenta_y_llega_la_bienvenida(self):
        self.registrar()
        codigo = codigo_de(mail.outbox[0])
        respuesta = self.client.post(reverse("confirmar_codigo"), {"email": "DAVID@ejemplo.com", "codigo": f"{codigo[:3]} {codigo[3:]}"}, follow=True)
        usuario = User.objects.get(username="david_laura")
        self.assertTrue(usuario.is_active)
        self.assertEqual(int(self.client.session["_auth_user_id"]), usuario.pk)
        self.assertContains(respuesta, "Correo confirmado")
        self.assertFalse(CodigoVerificacion.objects.exists())
        bienvenida = mail.outbox[-1]
        self.assertEqual(bienvenida.subject, "Bienvenido a NEXALYS Tec")
        self.assertIn(">Explorar el catálogo</a>", html_de(bienvenida))

    def test_el_enlace_tambien_envia_la_bienvenida(self):
        self.registrar()
        ruta = re.search(r"(/registro/confirmar/\S+)", mail.outbox[0].body).group(1)
        self.client.get(ruta)
        self.assertEqual(mail.outbox[-1].subject, "Bienvenido a NEXALYS Tec")

    def test_codigo_equivocado_vencido_o_reemplazado(self):
        self.registrar()
        primero = codigo_de(mail.outbox[0])
        equivocado = "000000" if primero != "000000" else "111111"
        respuesta = self.client.post(reverse("confirmar_codigo"), {"email": "david@ejemplo.com", "codigo": equivocado}, follow=True)
        self.assertContains(respuesta, "El código no es correcto o ya venció")
        # Reenviar: el código anterior deja de servir.
        self.client.post(reverse("reenviar_confirmacion"), {"email": "david@ejemplo.com"})
        segundo = codigo_de(mail.outbox[-1])
        if segundo != primero:
            self.client.post(reverse("confirmar_codigo"), {"email": "david@ejemplo.com", "codigo": primero})
            self.assertFalse(User.objects.get(username="david_laura").is_active)
        # Vencido (más de 24 horas).
        CodigoVerificacion.objects.update(creado=timezone.now() - timedelta(hours=25))
        self.client.post(reverse("confirmar_codigo"), {"email": "david@ejemplo.com", "codigo": segundo})
        self.assertFalse(User.objects.get(username="david_laura").is_active)

    def test_cinco_codigos_equivocados_hacen_esperar(self):
        self.registrar()
        bueno = codigo_de(mail.outbox[0])
        malo = "123456" if bueno != "123456" else "654321"
        for _ in range(5):
            self.client.post(reverse("confirmar_codigo"), {"email": "david@ejemplo.com", "codigo": malo})
        respuesta = self.client.post(reverse("confirmar_codigo"), {"email": "david@ejemplo.com", "codigo": bueno}, follow=True)
        self.assertContains(respuesta, "Demasiados intentos")
        self.assertFalse(User.objects.get(username="david_laura").is_active)

    def test_la_pagina_de_espera_tiene_el_campo_del_codigo(self):
        self.registrar()
        respuesta = self.client.get(reverse("confirmacion_pendiente"))
        self.assertContains(respuesta, f'action="{reverse("confirmar_codigo")}"')
        self.assertContains(respuesta, 'autocomplete="one-time-code"')
        self.assertContains(respuesta, 'name="email" value="david@ejemplo.com"')


@override_settings(SITIO_URL=SITIO)
class VerificacionTiendaTests(TestCase):
    def setUp(self):
        self.client.post(reverse("tiendas:registro"), DATOS_TIENDA)
        self.tienda = Tienda.objects.get(nombre=DATOS_TIENDA["nombre_tienda"])

    def test_correo_con_boton_y_codigo(self):
        html = html_de(mail.outbox[0])
        self.assertIn(">Verificar mi tienda</a>", html)
        self.assertIn(f'href="{SITIO}/tiendas/verificar/', html)
        self.assertIn(DATOS_TIENDA["nombre_tienda"], html)
        self.assertContains(self.client.get(reverse("tiendas:panel")), f'action="{reverse("tiendas:verificar_codigo")}"')

    def test_el_codigo_activa_la_tienda_y_llega_la_bienvenida(self):
        codigo = codigo_de(mail.outbox[0])
        respuesta = self.client.post(reverse("tiendas:verificar_codigo"), {"codigo": codigo}, follow=True)
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.estado, Tienda.Estado.ACTIVA)
        self.assertContains(respuesta, "Correo verificado")
        self.assertEqual(mail.outbox[-1].subject, f"{self.tienda.nombre} ya está activa en NEXALYS Tec")
        self.assertIn(">Ir a mi panel</a>", html_de(mail.outbox[-1]))

    def test_codigo_equivocado(self):
        bueno = codigo_de(mail.outbox[0])
        malo = "000000" if bueno != "000000" else "111111"
        respuesta = self.client.post(reverse("tiendas:verificar_codigo"), {"codigo": malo}, follow=True)
        self.assertContains(respuesta, "El código no es correcto o ya venció")
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.estado, Tienda.Estado.PENDIENTE)


@override_settings(SITIO_URL=SITIO)
class OtrosCorreosTests(TestCase):
    def test_recuperar_contrasena(self):
        User.objects.create_user("ana", "ana@ejemplo.com", CLAVE, first_name="Ana")
        self.client.post(reverse("password_reset"), {"email": "ana@ejemplo.com"})
        correo = mail.outbox[0]
        self.assertEqual(correo.subject, "Recupera tu contraseña de NEXALYS Tec")
        html = html_de(correo)
        self.assertIn(">Crear nueva contraseña</a>", html)
        self.assertIn(f'href="{SITIO}/', html)
        self.assertIn("Tu usuario es <strong>ana</strong>", html)
        self.assertIn("funciona hasta", correo.body)
