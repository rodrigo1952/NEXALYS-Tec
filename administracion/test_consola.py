"""Consola del administrador: entrada directa, menú lateral, resumen y claves temporales."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cuentas.clave_temporal import CLAVE_SESION, generar_clave
from cuentas.models import ClaveTemporal
from tiendas.models import Tienda
from tiendas.tests import crear_tienda

from .models import AccionAdmin

CLAVE = "ClaveSegura#2026"


def crear_admin(usuario="jefe"):
    admin = User.objects.create_user(usuario, f"{usuario}@ejemplo.com", CLAVE)
    admin.groups.add(Group.objects.get_or_create(name="Administrador")[0])
    return admin


def crear_cliente(usuario="cliente1"):
    cliente = User.objects.create_user(usuario, f"{usuario}@ejemplo.com", CLAVE)
    cliente.groups.add(Group.objects.get(name="Cliente"))
    return cliente


class EntradaYMarcoTests(TestCase):
    def setUp(self):
        self.admin = crear_admin()

    def test_el_admin_entra_directo_a_la_consola(self):
        respuesta = self.client.post(reverse("login"), {"username": "jefe", "password": CLAVE, "tipo": "cliente"})
        self.assertRedirects(respuesta, reverse("panel_admin"), fetch_redirect_response=False)

    def test_la_consola_tiene_su_propio_marco(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("panel_admin"))
        self.assertContains(respuesta, 'id="consola-menu"')
        self.assertContains(respuesta, "Ver página pública")
        for nombre in ("administracion:tiendas", "administracion:productos", "administracion:usuarios",
                       "administracion:ventas", "administracion:historial"):
            self.assertContains(respuesta, f'href="{reverse(nombre)}"')
        # Sin buscador, sin barra de categorías, sin Inicio/Catálogo en el menú y sin pie de página.
        self.assertNotContains(respuesta, 'id="buscar-menu"')
        self.assertNotContains(respuesta, 'class="barra-categorias"')
        self.assertNotContains(respuesta, 'class="navbar-nav menu-secciones')
        self.assertNotContains(respuesta, 'class="pie-marca')

    def test_globito_de_tiendas_por_verificar(self):
        crear_tienda("tienda2", "Tienda Dos", "922222222", estado=Tienda.Estado.PENDIENTE)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("administracion:usuarios")), 'title="Tiendas por verificar">1</span>')

    def test_en_la_pagina_publica_administracion_va_primero(self):
        self.client.force_login(self.admin)
        html = self.client.get(reverse("inicio")).content.decode()
        menu = html[html.index('class="navbar-nav menu-secciones'):]
        self.assertLess(menu.index(f'href="{reverse("panel_admin")}"'), menu.index(f'href="{reverse("inicio")}"'))


class ResumenTests(TestCase):
    def setUp(self):
        self.admin = crear_admin()
        self.client.force_login(self.admin)

    def test_tareas_grafico_y_ultimas_acciones(self):
        crear_tienda("tienda2", "Tienda Pendiente", "922222222", estado=Tienda.Estado.PENDIENTE)
        AccionAdmin.objects.create(admin=self.admin, admin_nombre="jefe", tipo=AccionAdmin.Tipo.OCULTAR_PRODUCTO,
                                   objetivo="Producto «X»", motivo="Precio falso")
        respuesta = self.client.get(reverse("panel_admin"))
        self.assertContains(respuesta, "Tareas pendientes")
        self.assertContains(respuesta, "Tienda Pendiente")
        self.assertContains(respuesta, 'id="grafico-ventas-admin"')
        self.assertContains(respuesta, "Chart.js")
        self.assertEqual(len(respuesta.context["grafico_montos"]), 6)
        self.assertContains(respuesta, "Últimas acciones")
        self.assertContains(respuesta, "Producto «X»")

    def test_todo_al_dia(self):
        self.assertContains(self.client.get(reverse("panel_admin")), "Todo al día")


class RestablecerClaveTests(TestCase):
    def setUp(self):
        self.admin = crear_admin()
        self.cliente = crear_cliente()
        self.tienda = crear_tienda()
        self.client.force_login(self.admin)

    def url(self, usuario):
        return reverse("administracion:usuario_clave", args=[usuario.pk])

    def restablecer(self, usuario, **datos):
        return self.client.post(self.url(usuario), datos or {"motivo": "olvido"})

    def test_la_clave_es_facil_de_dictar(self):
        clave = generar_clave()
        self.assertRegex(clave, r"^[A-Za-z2-9]{4}-[A-Za-z2-9]{4}-[A-Za-z2-9]{4}$")
        self.assertNotRegex(clave, r"[01OIl]")

    def test_genera_la_clave_y_la_muestra_una_vez(self):
        respuesta = self.restablecer(self.cliente)
        self.assertEqual(respuesta.status_code, 200)
        clave = respuesta.context["clave"]
        self.assertContains(respuesta, clave)
        self.assertIn("no-store", respuesta["Cache-Control"])
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.check_password(clave))
        registro = ClaveTemporal.objects.get(usuario=self.cliente)
        self.assertAlmostEqual((registro.vence - registro.creada).total_seconds(), 24 * 3600, delta=2)
        self.assertNotIn(clave, str(ClaveTemporal.objects.values()))  # nunca se guarda la clave
        accion = AccionAdmin.objects.get(tipo=AccionAdmin.Tipo.RESTABLECER_CLAVE)
        self.assertEqual(accion.motivo, "Olvidó su contraseña")
        self.assertEqual(accion.usuario_afectado, self.cliente)
        self.assertNotIn(clave, accion.motivo)

    def test_otro_motivo_pide_detalle(self):
        respuesta = self.restablecer(self.cliente, motivo="otro", detalle="")
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(ClaveTemporal.objects.exists())
        self.restablecer(self.cliente, motivo="otro", detalle="Lo pidió en la tienda con su DNI")
        self.assertEqual(AccionAdmin.objects.get().motivo, "Otro motivo. Lo pidió en la tienda con su DNI")

    def test_solo_clientes_y_tiendas_activos(self):
        otro_admin = crear_admin("jefe2")
        for usuario in (otro_admin, self.admin):
            respuesta = self.client.get(self.url(usuario))
            self.assertRedirects(respuesta, reverse("administracion:usuarios"))
        User.objects.filter(pk=self.cliente.pk).update(is_active=False)
        self.assertRedirects(self.client.get(self.url(self.cliente)), reverse("administracion:usuarios"))
        self.assertEqual(self.client.get(self.url(self.tienda.usuario)).status_code, 200)
        self.assertFalse(ClaveTemporal.objects.exists())

    def test_cliente_y_tienda_no_pueden_restablecer(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(self.url(self.tienda.usuario)).status_code, 403)

    def test_entrar_con_la_clave_obliga_a_crear_una_nueva(self):
        clave = self.restablecer(self.tienda.usuario).context["clave"]
        self.client.logout()
        respuesta = self.client.post(reverse("login"), {"username": "tienda1", "password": clave, "tipo": "tienda"})
        self.assertTrue(self.client.session.get(CLAVE_SESION))
        # Cualquier página lo devuelve a «Crea tu nueva contraseña».
        self.assertRedirects(self.client.get(reverse("catalogo:mis_productos")), reverse("clave_temporal"))
        respuesta = self.client.get(reverse("clave_temporal"))
        self.assertContains(respuesta, "Crea tu nueva contraseña")
        # No puede repetir la clave temporal.
        respuesta = self.client.post(reverse("clave_temporal"), {"new_password1": clave, "new_password2": clave})
        self.assertContains(respuesta, "distinta a la clave temporal")
        nueva = "MiClaveNueva#2026"
        respuesta = self.client.post(reverse("clave_temporal"), {"new_password1": nueva, "new_password2": nueva})
        self.assertRedirects(respuesta, reverse("catalogo:mis_productos"), fetch_redirect_response=False)
        self.assertFalse(ClaveTemporal.objects.exists())
        self.assertIsNone(self.client.session.get(CLAVE_SESION))
        self.assertEqual(self.client.get(reverse("catalogo:mis_productos")).status_code, 200)  # sigue con su sesión

    def test_la_clave_vence_a_las_24_horas(self):
        clave = self.restablecer(self.cliente).context["clave"]
        ClaveTemporal.objects.update(vence=timezone.now() - timedelta(minutes=1))
        self.client.logout()
        respuesta = self.client.post(reverse("login"), {"username": "cliente1", "password": clave, "tipo": "cliente"})
        self.assertContains(respuesta, "Tu clave temporal venció")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_si_la_cambio_por_otro_camino_ya_no_cuenta(self):
        self.restablecer(self.cliente)
        self.cliente.refresh_from_db()
        self.cliente.set_password("OtraClave#2026")
        self.cliente.save()
        ClaveTemporal.objects.update(vence=timezone.now() - timedelta(minutes=1))
        self.client.logout()
        respuesta = self.client.post(reverse("login"), {"username": "cliente1", "password": "OtraClave#2026", "tipo": "cliente"})
        self.assertRedirects(respuesta, reverse("inicio"), fetch_redirect_response=False)
        self.assertFalse(ClaveTemporal.objects.exists())
        self.assertIsNone(self.client.session.get(CLAVE_SESION))

    def test_la_lista_muestra_el_boton_y_la_clave_pendiente(self):
        self.restablecer(self.cliente)
        respuesta = self.client.get(reverse("administracion:usuarios"))
        self.assertContains(respuesta, f'href="{self.url(self.cliente)}"')
        self.assertContains(respuesta, f'href="{self.url(self.tienda.usuario)}"')
        self.assertNotContains(respuesta, f'href="{self.url(self.admin)}"')
        self.assertContains(respuesta, "Clave temporal")
        self.assertContains(self.client.get(reverse("administracion:historial")), "Restableció una contraseña")
