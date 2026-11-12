"""Aviso de errores: cada error 500 queda en la consola del administrador (Control → Errores)."""
from django.contrib.auth.models import User
from django.core import mail
from django.http import HttpResponse
from django.test import Client, TestCase, override_settings
from django.urls import include, path, reverse

from .models import ErrorRegistrado
from .registro_errores import MAXIMO_GUARDADOS

CLAVE = "ClaveSegura#2026"


def vista_que_falla(request, numero=0):
    raise ValueError(f"Algo salió mal con el número {numero}")


def vista_normal(request):
    return HttpResponse("ok")


urlpatterns = [
    path("falla/<int:numero>/", vista_que_falla),
    path("bien/", vista_normal),
    path("", include("config.urls")),
]


@override_settings(ROOT_URLCONF=__name__)
class RegistroDeErroresTests(TestCase):
    def setUp(self):
        self.visitante = Client(raise_request_exception=False)

    def test_un_error_500_queda_guardado(self):
        respuesta = self.visitante.post("/falla/7/", {"password": "MiClave123"})
        self.assertEqual(respuesta.status_code, 500)
        error = ErrorRegistrado.objects.get()
        self.assertEqual(error.tipo, "ValueError")
        self.assertEqual(error.mensaje, "Algo salió mal con el número 7")
        self.assertEqual((error.ruta, error.metodo, error.veces, error.revisado), ("/falla/7/", "POST", 1, False))
        self.assertIn("vista_que_falla", error.detalle)
        self.assertNotIn("MiClave123", error.detalle)  # no guarda lo que escribieron

    def test_errores_iguales_se_juntan(self):
        for numero in (1, 2, 3):
            self.visitante.get(f"/falla/{numero}/")
        error = ErrorRegistrado.objects.get()
        self.assertEqual(error.veces, 3)
        self.assertEqual(error.mensaje, "Algo salió mal con el número 3")

    def test_si_vuelve_a_pasar_aparece_de_nuevo(self):
        self.visitante.get("/falla/1/")
        ErrorRegistrado.objects.update(revisado=True)
        self.visitante.get("/falla/1/")
        self.assertFalse(ErrorRegistrado.objects.get().revisado)

    def test_guarda_la_cuenta_afectada(self):
        usuario = User.objects.create_user("ana", "a@ejemplo.com", CLAVE)
        self.visitante.force_login(usuario)
        self.visitante.get("/falla/1/")
        self.assertEqual(ErrorRegistrado.objects.get().usuario, "ana")

    def test_paginas_que_funcionan_y_404_no_se_guardan(self):
        self.visitante.get("/bien/")
        self.visitante.get("/no-existe/")
        self.assertFalse(ErrorRegistrado.objects.exists())

    def test_se_conservan_solo_los_mas_recientes(self):
        from django.utils import timezone

        ErrorRegistrado.objects.bulk_create(
            ErrorRegistrado(firma=f"f{n}", tipo="X", ruta="/", ultima=timezone.now()) for n in range(MAXIMO_GUARDADOS)
        )
        self.visitante.get("/falla/1/")
        self.assertEqual(ErrorRegistrado.objects.count(), MAXIMO_GUARDADOS)
        self.assertTrue(ErrorRegistrado.objects.filter(tipo="ValueError").exists())

    @override_settings(DEBUG=False, ADMINS=["admin@ejemplo.com"])
    def test_correo_al_administrador_cuando_hay_correo_real(self):
        self.visitante.get("/falla/1/")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["admin@ejemplo.com"])
        self.assertIn("ValueError", mail.outbox[0].subject + mail.outbox[0].body)


class ConsolaDeErroresTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", "admin@ejemplo.com", CLAVE)
        self.client.force_login(self.admin)
        from django.utils import timezone

        self.error = ErrorRegistrado.objects.create(
            firma="a", tipo="ValueError", mensaje="Algo salió mal", ruta="/catalogo/", metodo="GET",
            detalle="Traceback (most recent call last): ...", veces=4, ultima=timezone.now(),
        )

    def test_lista_con_globo_y_tarea_pendiente(self):
        respuesta = self.client.get(reverse("administracion:errores"))
        self.assertContains(respuesta, "<strong>ValueError</strong>: Algo salió mal")
        self.assertContains(respuesta, "<code>GET /catalogo/</code>")
        self.assertContains(respuesta, '<span class="consola__globo" title="Errores sin revisar">1</span>')
        resumen = self.client.get(reverse("panel_admin"))
        self.assertContains(resumen, "1 error de la página")
        self.assertContains(resumen, f'href="{reverse("administracion:errores")}"')

    def test_marcar_como_revisado(self):
        respuesta = self.client.post(reverse("administracion:errores_revisado"), {"pk": self.error.pk}, follow=True)
        self.assertContains(respuesta, "1 error marcado como revisado.")
        self.assertContains(respuesta, "No hay errores sin revisar.")
        self.assertNotContains(self.client.get(reverse("panel_admin")), "error de la página")
        self.assertContains(self.client.get(reverse("administracion:errores") + "?ver=todos"), "Algo salió mal")

    def test_marcar_todos(self):
        ErrorRegistrado.objects.create(firma="b", tipo="KeyError", ruta="/", ultima=self.error.ultima)
        self.client.post(reverse("administracion:errores_revisado"))
        self.assertFalse(ErrorRegistrado.objects.filter(revisado=False).exists())

    def test_solo_el_administrador(self):
        cliente = User.objects.create_user("cli", "c@ejemplo.com", CLAVE)
        self.client.force_login(cliente)
        self.assertEqual(self.client.get(reverse("administracion:errores")).status_code, 403)
        self.assertEqual(self.client.post(reverse("administracion:errores_revisado")).status_code, 403)
