"""Etapa 6: una tienda suspendida que no se reactiva en 90 días se elimina sola."""

import io
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from catalogo.models import Producto
from inventario.models import LineaVenta, Movimiento, Venta
from tiendas.models import Tienda

from . import limpieza
from .models import AccionAdmin
from .tests import BaseAdministracion


class EliminacionAutomaticaTests(BaseAdministracion):
    def suspender_hace(self, dias):
        self.tienda.suspender("Precios publicados falsos")
        Tienda.objects.filter(pk=self.tienda.pk).update(suspendida_en=timezone.now() - timedelta(days=dias))
        self.tienda.refresh_from_db()

    def test_suspender_guarda_la_fecha_y_reactivar_la_borra(self):
        self.tienda.suspender("Motivo de prueba")
        self.assertIsNotNone(self.tienda.suspendida_en)
        self.assertEqual(self.tienda.dias_para_eliminacion, 90)
        self.tienda.reactivar()
        self.assertIsNone(self.tienda.suspendida_en)
        self.assertIsNone(self.tienda.fecha_eliminacion)

    def test_antes_de_90_dias_no_se_elimina(self):
        self.suspender_hace(89)
        self.assertEqual(limpieza.ejecutar(), (0, 0))
        self.assertTrue(Tienda.objects.filter(pk=self.tienda.pk).exists())

    def test_a_los_90_dias_se_elimina_todo(self):
        usuario_id = self.tienda.usuario_id
        self.suspender_hace(90)
        self.assertEqual(limpieza.ejecutar()[0], 1)
        self.assertFalse(Tienda.objects.exists())
        self.assertFalse(Producto.objects.exists())
        self.assertFalse(User.objects.filter(pk=usuario_id).exists())
        accion = AccionAdmin.objects.get(tipo=AccionAdmin.Tipo.ELIMINACION_AUTOMATICA)
        self.assertEqual(accion.admin_nombre, "Sistema (automático)")
        self.assertIn("Precios publicados falsos", accion.motivo)

    def test_las_ventas_se_conservan_anonimas(self):
        self.crear_venta(2)
        self.suspender_hace(120)
        limpieza.ejecutar()
        venta = Venta.objects.get()
        self.assertIsNone(venta.tienda)
        self.assertEqual(venta.tienda_nombre, "Tienda eliminada")
        self.assertEqual(venta.cliente_nombre, "Cliente anónimo")
        self.assertEqual(venta.total, Decimal("1400.00"))
        linea = LineaVenta.objects.get()
        self.assertIsNone(linea.producto)
        self.assertEqual(linea.producto_nombre, "Galaxy A15")
        self.assertFalse(Movimiento.objects.exists())  # el kardex era privado de la tienda
        # Las estadísticas del administrador no cambian.
        respuesta = self.client.get(reverse("administracion:ventas"))
        self.assertEqual(respuesta.context["total_general"], Decimal("1400.00"))
        self.assertContains(respuesta, "Tienda eliminada")

    def test_una_tienda_reactivada_no_se_elimina(self):
        self.suspender_hace(100)
        self.tienda.reactivar()
        limpieza.ejecutar()
        self.assertTrue(Tienda.objects.filter(pk=self.tienda.pk).exists())

    def test_entrar_al_panel_ejecuta_la_limpieza(self):
        self.suspender_hace(95)
        respuesta = self.client.get(reverse("panel_admin"), follow=True)
        self.assertFalse(Tienda.objects.exists())
        self.assertContains(respuesta, "Se eliminaron automáticamente 1 tienda")

    def test_comando_limpiar_cuentas(self):
        self.suspender_hace(91)
        salida = io.StringIO()
        call_command("limpiar_cuentas", stdout=salida)
        self.assertIn("Tiendas eliminadas: 1", salida.getvalue())

    def test_avisos_con_la_fecha_limite(self):
        self.suspender_hace(80)
        self.assertContains(self.client.get(reverse("panel_admin")), "se eliminan solas a los 90 días")
        self.assertContains(self.client.get(reverse("administracion:tienda_detalle", args=[self.tienda.pk])), "faltan 10 días")
        self.client.force_login(self.tienda.usuario)
        self.assertContains(self.client.get(reverse("tiendas:panel")), "faltan 10 días")

    def test_la_confirmacion_de_suspender_avisa_los_90_dias(self):
        respuesta = self.client.get(reverse("administracion:tienda_suspender", args=[self.tienda.pk]))
        self.assertContains(respuesta, "Si no la reactivas en 90 días")
