"""Destacados del Inicio por turnos entre tiendas, filtro «Destacados» y «Agotados» sin los ocultos."""

from datetime import date

from django.urls import reverse

from tiendas.tests import crear_tienda

from .destacados import destacados_en_turnos
from .models import Producto
from .tests import BaseCatalogo


class DestacadosPorTurnosTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.tiendas = [self.tienda, self.otra_tienda] + [
            crear_tienda(f"tienda{n}", f"Tienda {n}", f"9{n}0000000"[:9]) for n in range(3, 8)
        ]
        for tienda in self.tiendas:  # 7 tiendas × 3 destacados = 21
            for n in range(3):
                self.crear_producto(tienda=tienda, nombre=f"{tienda.nombre} - {n}", destacado=True)

    def test_primero_uno_de_cada_tienda(self):
        elegidos, total = destacados_en_turnos(Producto.objects.visibles(), hoy=date(2026, 11, 2))
        self.assertEqual(total, 21)
        self.assertEqual(len(elegidos), 8)
        tiendas_primera_vuelta = {p.tienda_id for p in elegidos[:7]}
        self.assertEqual(len(tiendas_primera_vuelta), 7)  # las 7 tiendas salen al menos una vez

    def test_el_turno_rota_cada_dia(self):
        visibles = Producto.objects.visibles()
        hoy, _ = destacados_en_turnos(visibles, hoy=date(2026, 11, 2))
        manana, _ = destacados_en_turnos(visibles, hoy=date(2026, 11, 3))
        otra_vez_hoy, _ = destacados_en_turnos(visibles, hoy=date(2026, 11, 2))
        self.assertNotEqual(hoy[0].tienda_id, manana[0].tienda_id)
        self.assertEqual([p.pk for p in hoy], [p.pk for p in otra_vez_hoy])  # todo el día igual
        # En 7 días, cada tienda va primero una vez.
        primeras = {destacados_en_turnos(visibles, hoy=date(2026, 11, d))[0][0].tienda_id for d in range(1, 8)}
        self.assertEqual(len(primeras), 7)

    def test_inicio_ofrece_ver_todos(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertEqual(len(respuesta.context["destacados"]), 8)
        self.assertContains(respuesta, "Ver todos los destacados (21)")
        self.assertContains(respuesta, f'{reverse("catalogo:catalogo")}?destacados=on')

    def test_filtro_destacados_en_el_catalogo(self):
        self.crear_producto(nombre="Normal")
        respuesta = self.client.get(reverse("catalogo:catalogo"), {"destacados": "on"})
        self.assertEqual(respuesta.context["pagina"].paginator.count, 21)
        self.assertContains(respuesta, "Productos destacados")
        self.assertEqual(respuesta.context["disponibilidad"]["destacados"], 21)


class PocosDestacadosTests(BaseCatalogo):
    def test_sin_enlace_si_caben_todos(self):
        self.crear_producto(nombre="Estrella", destacado=True)
        respuesta = self.client.get(reverse("inicio"))
        self.assertNotContains(respuesta, "Ver todos los destacados")


class AgotadosSoloVisiblesTests(BaseCatalogo):
    def test_agotado_y_oculto_va_solo_a_ocultos(self):
        self.client.force_login(self.tienda.usuario)
        self.crear_producto(nombre="Agotado visible", stock=0)
        self.crear_producto(nombre="Agotado oculto", stock=0, activo=False)
        self.crear_producto(nombre="Agotado ocultado por admin", stock=0, oculto_por_admin=True)
        url = reverse("catalogo:mis_productos")

        def nombres(ver):
            return sorted(p.nombre for p in self.client.get(url, {"ver": ver}).context["pagina"])

        self.assertEqual(nombres("agotados"), ["Agotado visible"])
        self.assertEqual(nombres("ocultos"), ["Agotado ocultado por admin", "Agotado oculto"])
        resumen = self.client.get(url).context["resumen"]
        self.assertEqual((resumen["agotados"], resumen["ocultos"]), (1, 2))

    def test_el_aviso_del_menu_cuenta_solo_lo_visible(self):
        from inventario.reportes import cantidad_de_alertas

        self.crear_producto(nombre="Agotado visible", stock=0)
        self.crear_producto(nombre="Agotado oculto", stock=0, activo=False)
        self.assertEqual(cantidad_de_alertas(self.tienda), 1)
