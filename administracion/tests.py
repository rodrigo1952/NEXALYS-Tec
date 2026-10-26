"""
Pruebas del panel de administración con el diseño de NEXALYS.
Ejecutar con:  python manage.py test administracion
"""

from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Marca, Producto
from favoritos.models import Favorito
from inventario import servicios as inventario
from tiendas.models import Tienda
from tiendas.tests import crear_tienda

from .models import AccionAdmin

CLAVE = "ClaveSegura#2026"


def crear_cliente(usuario="cliente1"):
    user = User.objects.create_user(usuario, f"{usuario}@ejemplo.com", CLAVE)
    user.groups.add(Group.objects.get(name="Cliente"))
    return user


class BaseAdministracion(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", "admin@ejemplo.com", CLAVE)
        self.tienda = crear_tienda()
        self.producto = Producto.objects.create(
            tienda=self.tienda,
            categoria=Categoria.objects.get(nombre="Celulares"),
            marca=Marca.objects.get(nombre="Samsung"),
            nombre="Galaxy A15", precio=Decimal("700.00"), stock=5,
        )
        self.client.force_login(self.admin)

    def crear_venta(self, cantidad=2, tienda=None, producto=None):
        tienda, producto = tienda or self.tienda, producto or self.producto
        return inventario.registrar_venta(
            tienda, tienda.usuario, [inventario.LineaPedida(producto.pk, cantidad)], cliente_nombre="Ana Quispe",
        )


class AccesoTests(BaseAdministracion):
    URLS = [
        ("panel_admin", []),
        ("administracion:tiendas", []),
        ("administracion:productos", []),
        ("administracion:ventas", []),
        ("administracion:usuarios", []),
    ]

    def test_el_administrador_ve_todas_las_secciones(self):
        for nombre, args in self.URLS:
            with self.subTest(nombre):
                respuesta = self.client.get(reverse(nombre, args=args))
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, "⚙️ Administración")  # mismo menú en todas

    def test_cliente_y_tienda_no_entran(self):
        for usuario in (crear_cliente(), self.tienda.usuario):
            self.client.force_login(usuario)
            for nombre, args in self.URLS:
                with self.subTest(usuario=usuario.username, url=nombre):
                    self.assertEqual(self.client.get(reverse(nombre, args=args)).status_code, 403)

    def test_categorias_y_marcas_usan_el_mismo_menu(self):
        respuesta = self.client.get(reverse("catalogo:gestion_lista", args=["marcas"]))
        self.assertContains(respuesta, reverse("administracion:usuarios"))

    def test_resumen_muestra_los_numeros(self):
        crear_tienda("tienda2", "Tienda Dos", "922222222", estado=Tienda.Estado.PENDIENTE)
        crear_cliente()
        self.crear_venta()
        respuesta = self.client.get(reverse("panel_admin"))
        self.assertEqual(respuesta.context["tiendas_activas"], 1)
        self.assertEqual(respuesta.context["tiendas_pendientes"], 1)
        self.assertEqual(respuesta.context["clientes"], 1)
        self.assertEqual(respuesta.context["tiendas_con_ventas"], 1)
        self.assertEqual(respuesta.context["ventas_mes"], Decimal("1400.00"))
        self.assertContains(respuesta, "Django Admin")  # enlace de respaldo


class TiendasAdminTests(BaseAdministracion):
    def test_suspender_con_motivo_y_la_tienda_lo_ve(self):
        respuesta = self.client.post(
            reverse("administracion:tienda_suspender", args=[self.tienda.pk]),
            {"motivo": "Precios publicados falsos"},
        )
        self.assertRedirects(respuesta, reverse("administracion:tienda_detalle", args=[self.tienda.pk]))
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.estado, Tienda.Estado.SUSPENDIDA)
        self.assertFalse(Producto.objects.visibles().exists())

        self.client.force_login(self.tienda.usuario)
        self.assertContains(self.client.get(reverse("tiendas:panel")), "Precios publicados falsos")

    def test_suspender_sin_motivo_no_se_permite(self):
        respuesta = self.client.post(reverse("administracion:tienda_suspender", args=[self.tienda.pk]), {"motivo": ""})
        self.assertEqual(respuesta.status_code, 400)
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.estado, Tienda.Estado.ACTIVA)

    def test_reactivar_borra_el_motivo(self):
        self.tienda.verificada_en = self.tienda.creada_en
        self.tienda.save()
        self.tienda.suspender("Motivo de prueba")
        self.client.post(reverse("administracion:tienda_reactivar", args=[self.tienda.pk]))
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.estado, Tienda.Estado.ACTIVA)
        self.assertEqual(self.tienda.motivo_suspension, "")

    def test_reactivar_sin_correo_verificado_queda_pendiente(self):
        self.tienda.suspender("Motivo de prueba")  # crear_tienda no marca verificada_en
        self.client.post(reverse("administracion:tienda_reactivar", args=[self.tienda.pk]))
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.estado, Tienda.Estado.PENDIENTE)

    def test_filtrar_por_estado(self):
        crear_tienda("tienda2", "Tienda Suspendida", "922222222", estado=Tienda.Estado.SUSPENDIDA)
        respuesta = self.client.get(reverse("administracion:tiendas"), {"estado": "suspendida"})
        self.assertContains(respuesta, "Tienda Suspendida")
        self.assertNotContains(respuesta, "Tienda Uno")


class ProductosAdminTests(BaseAdministracion):
    def test_ocultar_con_motivo(self):
        respuesta = self.client.post(
            reverse("administracion:producto_ocultar", args=[self.producto.pk]),
            {"motivo": "Imagen que no corresponde"},
        )
        self.assertRedirects(respuesta, reverse("administracion:productos"))
        self.producto.refresh_from_db()
        self.assertTrue(self.producto.oculto_por_admin)
        self.assertFalse(Producto.objects.visibles().exists())
        # El cliente ya no puede ver el detalle.
        self.client.logout()
        self.assertEqual(self.client.get(reverse("catalogo:detalle", args=[self.producto.pk])).status_code, 404)

    def test_la_tienda_ve_el_motivo_y_no_puede_publicarlo(self):
        self.producto.oculto_por_admin = True
        self.producto.motivo_ocultamiento = "Imagen que no corresponde"
        self.producto.save()
        self.client.force_login(self.tienda.usuario)
        self.assertContains(self.client.get(reverse("catalogo:mis_productos")), "Imagen que no corresponde")
        # Aunque la tienda lo tenga "publicado", sigue fuera del catálogo.
        self.assertTrue(Producto.objects.get(pk=self.producto.pk).activo)
        self.assertFalse(Producto.objects.visibles().exists())

    def test_volver_a_mostrar(self):
        self.producto.oculto_por_admin = True
        self.producto.save()
        self.client.post(reverse("administracion:producto_mostrar", args=[self.producto.pk]))
        self.producto.refresh_from_db()
        self.assertFalse(self.producto.oculto_por_admin)
        self.assertTrue(Producto.objects.visibles().exists())

    def test_ocultar_sin_motivo_no_se_permite(self):
        self.client.post(reverse("administracion:producto_ocultar", args=[self.producto.pk]), {"motivo": ""})
        self.producto.refresh_from_db()
        self.assertFalse(self.producto.oculto_por_admin)

    def test_el_administrador_no_tiene_boton_editar(self):
        respuesta = self.client.get(reverse("administracion:productos"))
        self.assertContains(respuesta, "Galaxy A15")
        self.assertNotContains(respuesta, reverse("catalogo:editar", args=[self.producto.pk]))

    def test_favorito_de_producto_oculto_aparece_no_disponible(self):
        cliente = crear_cliente()
        Favorito.guardar(cliente, self.producto)
        self.producto.oculto_por_admin = True
        self.producto.save()
        self.client.force_login(cliente)
        self.assertContains(self.client.get(reverse("favoritos:lista")), "No disponible")


class VentasAdminTests(BaseAdministracion):
    def test_tabla_de_seis_meses_solo_con_totales(self):
        otra = crear_tienda("tienda2", "Tienda Dos", "922222222")
        producto_otra = Producto.objects.create(
            tienda=otra, categoria=self.producto.categoria, marca=self.producto.marca,
            nombre="Mouse", precio=Decimal("50.00"), stock=10,
        )
        self.crear_venta(2)                                     # 1400
        anulada = self.crear_venta(1)
        inventario.anular_venta(anulada, self.tienda.usuario, "Prueba de anulación")  # no cuenta
        self.crear_venta(3, tienda=otra, producto=producto_otra)  # 150
        respuesta = self.client.get(reverse("administracion:ventas"))
        self.assertEqual(len(respuesta.context["meses"]), 6)
        filas = respuesta.context["filas"]
        self.assertEqual([f["nombre"] for f in filas], ["Tienda Uno", "Tienda Dos"])  # de mayor a menor
        self.assertEqual(filas[0]["montos"][-1], Decimal("1400.00"))  # mes actual = última columna
        self.assertEqual(respuesta.context["total_general"], Decimal("1550.00"))
        # Privacidad: nada de clientes, costos ni ganancias.
        self.assertNotContains(respuesta, "Ana Quispe")
        self.assertNotContains(respuesta, ">Ganancia<")  # no hay columna de ganancia

    def test_tiendas_muestra_lo_vendido_en_el_mes(self):
        self.crear_venta(1)
        respuesta = self.client.get(reverse("administracion:tiendas"))
        self.assertContains(respuesta, "S/ 700.00")


class UsuariosAdminTests(BaseAdministracion):
    def test_lista_muestra_roles(self):
        crear_cliente()
        respuesta = self.client.get(reverse("administracion:usuarios"))
        self.assertContains(respuesta, "cliente1")
        self.assertContains(respuesta, "tienda1")

    def test_desactivar_y_reactivar(self):
        cliente = crear_cliente()
        self.client.post(reverse("administracion:usuario_desactivar", args=[cliente.pk]), {"motivo": "Comentarios ofensivos"})
        cliente.refresh_from_db()
        self.assertFalse(cliente.is_active)
        # Una cuenta desactivada no puede iniciar sesión.
        self.client.logout()
        self.assertFalse(self.client.login(username="cliente1", password=CLAVE))
        self.client.force_login(self.admin)
        self.client.post(reverse("administracion:usuario_reactivar", args=[cliente.pk]))
        cliente.refresh_from_db()
        self.assertTrue(cliente.is_active)

    def test_no_puede_desactivarse_a_si_mismo(self):
        self.client.post(reverse("administracion:usuario_desactivar", args=[self.admin.pk]), {"motivo": "Prueba de seguridad"})
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_eliminar_cliente_con_confirmacion(self):
        cliente = crear_cliente()
        url = reverse("administracion:usuario_eliminar", args=[cliente.pk])
        self.client.post(url, {})  # sin marcar la confirmación
        self.assertTrue(User.objects.filter(pk=cliente.pk).exists())
        self.client.post(url, {"confirmar": "on"})  # sin motivo
        self.assertTrue(User.objects.filter(pk=cliente.pk).exists())
        self.client.post(url, {"confirmar": "on", "motivo": "Cuenta duplicada"})
        self.assertFalse(User.objects.filter(pk=cliente.pk).exists())

    def test_eliminar_tienda_sin_ventas_borra_sus_productos(self):
        url = reverse("administracion:usuario_eliminar", args=[self.tienda.usuario.pk])
        self.assertContains(self.client.get(url), "1 producto")
        self.client.post(url, {"confirmar": "on", "motivo": "La tienda cerró"})
        self.assertFalse(Tienda.objects.exists())
        self.assertFalse(Producto.objects.exists())

    def test_tienda_con_ventas_no_se_elimina(self):
        self.crear_venta()
        url = reverse("administracion:usuario_eliminar", args=[self.tienda.usuario.pk])
        respuesta = self.client.post(url, {"confirmar": "on"}, follow=True)
        self.assertContains(respuesta, "historial")
        self.assertTrue(Tienda.objects.exists())

    def test_no_puede_eliminarse_a_si_mismo(self):
        self.client.post(reverse("administracion:usuario_eliminar", args=[self.admin.pk]), {"confirmar": "on"})
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())


class ConfirmacionEnDosPasosTests(BaseAdministracion):
    """Suspender, reactivar, desactivar y eliminar: el botón lleva a una confirmación con motivo."""

    def test_el_primer_paso_no_cambia_nada(self):
        cliente = crear_cliente()
        urls = [
            reverse("administracion:tienda_suspender", args=[self.tienda.pk]),
            reverse("administracion:usuario_desactivar", args=[cliente.pk]),
            reverse("administracion:usuario_eliminar", args=[cliente.pk]),
        ]
        for url in urls:
            with self.subTest(url):
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, 'name="motivo"')
        self.tienda.refresh_from_db()
        cliente.refresh_from_db()
        self.assertEqual(self.tienda.estado, Tienda.Estado.ACTIVA)
        self.assertTrue(cliente.is_active)

    def test_la_confirmacion_resume_lo_que_pasara(self):
        respuesta = self.client.get(reverse("administracion:tienda_suspender", args=[self.tienda.pk]))
        self.assertContains(respuesta, "1 producto publicado dejará de verse")

    def test_desactivar_sin_motivo_no_se_permite(self):
        cliente = crear_cliente()
        respuesta = self.client.post(reverse("administracion:usuario_desactivar", args=[cliente.pk]), {"motivo": ""})
        self.assertEqual(respuesta.status_code, 400)
        cliente.refresh_from_db()
        self.assertTrue(cliente.is_active)

    def test_reactivar_tambien_pide_confirmacion(self):
        self.tienda.suspender("Motivo de prueba")
        respuesta = self.client.get(reverse("administracion:tienda_reactivar", args=[self.tienda.pk]))
        self.assertContains(respuesta, "Motivo de la suspensión: Motivo de prueba")
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.estado, Tienda.Estado.SUSPENDIDA)

    def test_la_lista_de_usuarios_ya_no_desactiva_con_un_clic(self):
        cliente = crear_cliente()
        respuesta = self.client.get(reverse("administracion:usuarios"))
        self.assertContains(respuesta, f'href="{reverse("administracion:usuario_desactivar", args=[cliente.pk])}"')


class CuentaDeTiendaTests(BaseAdministracion):
    """Etapa 3: desactivar la cuenta de una tienda también la suspende."""

    def test_desactivar_cuenta_suspende_la_tienda_y_oculta_productos(self):
        self.client.post(
            reverse("administracion:usuario_desactivar", args=[self.tienda.usuario.pk]),
            {"motivo": "Precios falsos reiterados"},
        )
        self.tienda.refresh_from_db()
        self.assertFalse(self.tienda.usuario.is_active)
        self.assertEqual(self.tienda.estado, Tienda.Estado.SUSPENDIDA)
        self.assertEqual(self.tienda.motivo_suspension, "Precios falsos reiterados")
        self.assertFalse(Producto.objects.visibles().exists())
        self.client.logout()
        self.assertEqual(self.client.get(reverse("tiendas:perfil", args=[self.tienda.pk])).status_code, 404)

    def test_reactivar_cuenta_reactiva_la_tienda(self):
        self.tienda.verificada_en = self.tienda.creada_en
        self.tienda.save()
        usuario = self.tienda.usuario
        self.client.post(reverse("administracion:usuario_desactivar", args=[usuario.pk]), {"motivo": "Revisión de datos"})
        self.client.post(reverse("administracion:usuario_reactivar", args=[usuario.pk]))
        self.tienda.refresh_from_db()
        self.assertTrue(self.tienda.usuario.is_active)
        self.assertEqual(self.tienda.estado, Tienda.Estado.ACTIVA)
        self.assertTrue(Producto.objects.visibles().exists())

    def test_reactivar_tienda_reactiva_la_cuenta(self):
        self.tienda.verificada_en = self.tienda.creada_en
        self.tienda.save()
        self.client.post(reverse("administracion:usuario_desactivar", args=[self.tienda.usuario.pk]), {"motivo": "Revisión de datos"})
        self.client.post(reverse("administracion:tienda_reactivar", args=[self.tienda.pk]))
        self.tienda.refresh_from_db()
        self.assertTrue(self.tienda.usuario.is_active)
        self.assertEqual(self.tienda.estado, Tienda.Estado.ACTIVA)


class HistorialTests(BaseAdministracion):
    def test_cada_accion_queda_registrada_con_su_motivo(self):
        cliente = crear_cliente()
        self.client.post(reverse("administracion:tienda_suspender", args=[self.tienda.pk]), {"motivo": "Precios falsos"})
        self.client.post(reverse("administracion:usuario_desactivar", args=[cliente.pk]), {"motivo": "Spam en reseñas"})
        self.client.post(reverse("administracion:usuario_eliminar", args=[cliente.pk]), {"confirmar": "on", "motivo": "Cuenta falsa"})
        tipos = list(AccionAdmin.objects.order_by("id").values_list("tipo", flat=True))
        self.assertEqual(tipos, ["suspender_tienda", "desactivar_cuenta", "eliminar_cuenta"])

        respuesta = self.client.get(reverse("administracion:historial"))
        self.assertContains(respuesta, "Cuenta falsa")  # el motivo de la cuenta eliminada se conserva
        self.assertContains(respuesta, "cliente1")
        self.assertContains(respuesta, "admin")

    def test_filtrar_por_tipo(self):
        self.client.post(reverse("administracion:tienda_suspender", args=[self.tienda.pk]), {"motivo": "Precios falsos"})
        respuesta = self.client.get(reverse("administracion:historial"), {"tipo": "eliminar_cuenta"})
        self.assertNotContains(respuesta, "Precios falsos")

    def test_solo_el_administrador_ve_el_historial(self):
        self.client.force_login(crear_cliente())
        self.assertEqual(self.client.get(reverse("administracion:historial")).status_code, 403)


class IngresoCuentaDesactivadaTests(BaseAdministracion):
    def test_ve_el_motivo_solo_con_la_clave_correcta(self):
        cliente = crear_cliente()
        self.client.post(reverse("administracion:usuario_desactivar", args=[cliente.pk]), {"motivo": "Uso indebido de la página"})
        self.client.logout()
        respuesta = self.client.post(reverse("login"), {"username": "cliente1", "password": CLAVE})
        self.assertContains(respuesta, "Tu cuenta fue desactivada")
        self.assertContains(respuesta, "Uso indebido de la página")

        respuesta = self.client.post(reverse("login"), {"username": "cliente1", "password": "otra-clave"})
        self.assertNotContains(respuesta, "desactivada")
        self.assertContains(respuesta, "Usuario o contraseña incorrectos")
