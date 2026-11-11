"""Límite de intentos: 5 contraseñas equivocadas → 15 minutos; 3 correos por hora."""
from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from tiendas.models import Tienda
from tiendas.tests import crear_tienda

from . import limites
from .models import CorreoPendiente, IntentoAcceso

CLAVE = "ClaveSegura#2026"
AVISO = "Demasiados intentos. Vuelve a intentarlo en"


class IngresoConLimiteTests(TestCase):
    def setUp(self):
        self.cliente = User.objects.create_user("cliente1", "c@ejemplo.com", CLAVE)
        self.cliente.groups.add(Group.objects.get(name="Cliente"))
        self.url = reverse("login")

    def entrar(self, clave="mala", usuario="cliente1", ip="10.0.0.1"):
        return self.client.post(
            self.url, {"username": usuario, "password": clave, "tipo": "cliente"}, REMOTE_ADDR=ip
        )

    def test_cuatro_errores_aun_dejan_intentar(self):
        for _ in range(4):
            respuesta = self.entrar()
            self.assertContains(respuesta, "Usuario o contraseña incorrectos.")
        self.assertRedirects(self.entrar(CLAVE), reverse("inicio"), fetch_redirect_response=False)

    def test_al_quinto_error_espera_15_minutos(self):
        for _ in range(4):
            self.entrar()
        respuesta = self.entrar()
        self.assertContains(respuesta, f"{AVISO} 15 minutos.", status_code=429)
        self.assertNotContains(respuesta, "Usuario o contraseña incorrectos.", status_code=429)
        # Bloqueado: ni con la contraseña correcta entra, y el usuario escrito se conserva.
        respuesta = self.entrar(CLAVE)
        self.assertContains(respuesta, AVISO, status_code=429)
        self.assertContains(respuesta, 'value="cliente1"', status_code=429)
        self.assertIsNone(self.client.session.get("_auth_user_id"))
        # Mientras espera, sus intentos no se guardan.
        self.assertEqual(IntentoAcceso.objects.count(), 5)

    def test_pasados_15_minutos_puede_entrar(self):
        for _ in range(5):
            self.entrar()
        despues = timezone.now() + timedelta(minutes=15, seconds=1)
        with mock.patch("django.utils.timezone.now", return_value=despues):
            respuesta = self.entrar(CLAVE)
        self.assertEqual(respuesta.status_code, 302)

    def test_el_mensaje_dice_los_minutos_que_faltan(self):
        for _ in range(5):
            self.entrar()
        despues = timezone.now() + timedelta(minutes=14, seconds=30)
        with mock.patch("django.utils.timezone.now", return_value=despues):
            self.assertContains(self.entrar(CLAVE), f"{AVISO} 1 minuto.", status_code=429)

    def test_otra_conexion_no_queda_bloqueada(self):
        for _ in range(5):
            self.entrar(ip="10.0.0.1")
        self.assertEqual(self.entrar(CLAVE, ip="10.0.0.2").status_code, 302)

    def test_entrar_bien_borra_los_errores(self):
        for _ in range(4):
            self.entrar()
        self.entrar(CLAVE)
        self.client.logout()
        for _ in range(4):
            self.assertEqual(self.entrar().status_code, 200)

    def test_20_errores_desde_una_conexion_con_distintos_usuarios(self):
        for numero in range(20):
            self.entrar(usuario=f"alguien{numero}")
        self.assertContains(self.entrar(CLAVE), AVISO, status_code=429)

    def test_tipo_equivocado_con_clave_correcta_no_cuenta(self):
        for _ in range(6):
            self.client.post(self.url, {"username": "cliente1", "password": CLAVE, "tipo": "tienda"}, REMOTE_ADDR="10.0.0.1")
        self.assertEqual(IntentoAcceso.objects.count(), 0)

    def test_cuenta_sin_confirmar_con_su_clave_no_cuenta(self):
        self.cliente.is_active = False
        self.cliente.save()
        CorreoPendiente.objects.create(usuario=self.cliente)
        for _ in range(6):
            self.assertContains(self.entrar(CLAVE), "Primero confirma tu correo.")
        self.assertEqual(IntentoAcceso.objects.count(), 0)

    @override_settings(IP_CABECERA="HTTP_X_REAL_IP")
    def test_ip_desde_la_cabecera_del_hosting(self):
        for _ in range(5):
            self.client.post(self.url, {"username": "cliente1", "password": "mala"}, HTTP_X_REAL_IP="200.1.1.1")
        self.assertEqual(set(IntentoAcceso.objects.values_list("ip", flat=True)), {"200.1.1.1"})

    def test_los_registros_viejos_se_borran_solos(self):
        viejo = IntentoAcceso.objects.create(accion=limites.LOGIN, clave="x", ip="1.1.1.1")
        IntentoAcceso.objects.filter(pk=viejo.pk).update(creado=timezone.now() - timedelta(days=2))
        self.entrar()
        self.assertFalse(IntentoAcceso.objects.filter(pk=viejo.pk).exists())

    def test_no_guarda_la_contrasena(self):
        self.entrar("MiClaveSecreta123")
        intento = IntentoAcceso.objects.get()
        self.assertNotIn("MiClaveSecreta123", f"{intento.accion} {intento.clave} {intento.ip}")


class CorreosConLimiteTests(TestCase):
    def test_recuperar_contrasena_maximo_3_por_hora(self):
        User.objects.create_user("cliente1", "c@ejemplo.com", CLAVE)
        url = reverse("password_reset")
        for _ in range(3):
            self.assertRedirects(self.client.post(url, {"email": "c@ejemplo.com"}), reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 3)
        respuesta = self.client.post(url, {"email": "C@ejemplo.com"})
        self.assertContains(respuesta, f"{AVISO} 60 minutos.")
        self.assertEqual(len(mail.outbox), 3)

    def test_recuperar_con_correo_que_no_existe_tambien_tiene_limite(self):
        # Mismo trato exista o no la cuenta: así no se revela qué correos están registrados.
        url = reverse("password_reset")
        for _ in range(3):
            self.client.post(url, {"email": "nadie@ejemplo.com"})
        self.assertContains(self.client.post(url, {"email": "nadie@ejemplo.com"}), AVISO)

    def test_reenviar_confirmacion_maximo_3_por_hora(self):
        usuario = User.objects.create_user("nuevo", "n@ejemplo.com", CLAVE, is_active=False)
        CorreoPendiente.objects.create(usuario=usuario)
        url = reverse("reenviar_confirmacion")
        for _ in range(3):
            self.client.post(url, {"email": "n@ejemplo.com"})
        self.assertEqual(len(mail.outbox), 3)
        respuesta = self.client.post(url, {"email": "n@ejemplo.com"}, follow=True)
        self.assertContains(respuesta, AVISO)
        self.assertEqual(len(mail.outbox), 3)

    def test_reenviar_verificacion_de_tienda_maximo_3_por_hora(self):
        tienda = crear_tienda(estado=Tienda.Estado.PENDIENTE)
        self.client.force_login(tienda.usuario)
        url = reverse("tiendas:reenviar")
        for _ in range(3):
            self.client.post(url)
        self.assertEqual(len(mail.outbox), 3)
        respuesta = self.client.post(url, follow=True)
        self.assertContains(respuesta, AVISO)
        self.assertEqual(len(mail.outbox), 3)

    def test_diez_correos_distintos_desde_una_conexion(self):
        url = reverse("password_reset")
        for numero in range(10):
            self.client.post(url, {"email": f"persona{numero}@ejemplo.com"})
        self.assertContains(self.client.post(url, {"email": "otra@ejemplo.com"}), AVISO)


class FinDelBloqueoTests(TestCase):
    def test_cuenta_desde_el_intento_que_completa_el_limite(self):
        ahora = timezone.now()
        periodo = timedelta(minutes=15)
        minutos = lambda *ms: [ahora + timedelta(minutes=m) for m in ms]
        self.assertIsNone(limites._fin_del_bloqueo(minutos(0, 1, 2, 3), 5, periodo))
        self.assertEqual(limites._fin_del_bloqueo(minutos(0, 1, 2, 3, 14), 5, periodo), ahora + timedelta(minutes=29))
        # 5 errores repartidos en más de 15 minutos no bloquean.
        self.assertIsNone(limites._fin_del_bloqueo(minutos(0, 4, 8, 12, 16), 5, periodo))
