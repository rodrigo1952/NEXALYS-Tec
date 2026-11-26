"""Nov 2026: Ventas por tienda con píldoras de periodo (últimos 6 meses o un año completo)."""

from datetime import datetime
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from inventario.models import Venta

from .tests import BaseAdministracion


class PeriodoDeVentasTests(BaseAdministracion):
    def venta_en(self, anio, mes, cantidad=1):
        venta = self.crear_venta(cantidad)
        fecha = timezone.make_aware(datetime(anio, mes, 15, 12, 0))
        Venta.objects.filter(pk=venta.pk).update(fecha=fecha)
        return venta

    def test_por_defecto_ultimos_seis_meses_y_pildoras_de_los_anios_con_ventas(self):
        anio_pasado = timezone.localdate().year - 1
        self.venta_en(anio_pasado, 3)
        respuesta = self.client.get(reverse("administracion:ventas"))
        self.assertEqual(len(respuesta.context["meses"]), 6)
        self.assertEqual(respuesta.context["periodo"], "")
        self.assertEqual(respuesta.context["anios"], [anio_pasado + 1, anio_pasado])
        self.assertContains(respuesta, "Últimos 6 meses")
        self.assertContains(respuesta, f'?periodo={anio_pasado}">{anio_pasado}</a>')
        self.assertEqual(respuesta.context["total_general"], Decimal("0"))  # la venta vieja no entra

    def test_un_anio_muestra_sus_12_meses_y_solo_sus_ventas(self):
        anio_pasado = timezone.localdate().year - 1
        self.venta_en(anio_pasado, 3, cantidad=2)   # 1400 en marzo
        self.venta_en(anio_pasado - 1, 12)          # otro año: no cuenta
        self.crear_venta(1)                         # este año: no cuenta
        respuesta = self.client.get(reverse("administracion:ventas"), {"periodo": anio_pasado})
        self.assertEqual(respuesta.context["meses"][0], f"Ene {anio_pasado}")
        self.assertEqual(len(respuesta.context["meses"]), 12)
        fila = respuesta.context["filas"][0]
        self.assertEqual(fila["montos"][2], Decimal("1400.00"))
        self.assertEqual(respuesta.context["total_general"], Decimal("1400.00"))
        self.assertContains(respuesta, f"Año {anio_pasado}")

    def test_meses_que_aun_no_llegan_se_ven_con_raya(self):
        hoy = timezone.localdate()
        respuesta = self.client.get(reverse("administracion:ventas"), {"periodo": hoy.year})
        futuros = [futuro for _, futuro in respuesta.context["filas"][0]["celdas"]]
        self.assertEqual(futuros, [mes > hoy.month for mes in range(1, 13)])

    def test_un_anio_sin_ventas_vuelve_a_los_ultimos_seis_meses(self):
        respuesta = self.client.get(reverse("administracion:ventas"), {"periodo": "1999"})
        self.assertEqual(respuesta.context["periodo"], "")
        self.assertEqual(len(respuesta.context["meses"]), 6)
