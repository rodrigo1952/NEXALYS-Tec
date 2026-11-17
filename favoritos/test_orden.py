"""
Orden de «Mis favoritos» (nov 2026): «Recomendado» por grupos (bajaron de precio → volvieron a tener stock
→ los demás → agotados), «Ordenar por» que se recuerda y el texto «Bajó S/ X desde que lo guardaste».
"""

from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from catalogo.models import Producto

from .models import Favorito, PreferenciaFavoritos
from .tests import BaseFavoritos


class FechaDeReposicionTests(BaseFavoritos):
    def test_se_anota_cuando_un_agotado_vuelve_a_tener_stock(self):
        self.assertIsNone(self.producto.repuesto_el)  # se creó con stock: no «volvió»
        self.producto.stock = 0
        self.producto.save()
        self.assertIsNone(self.producto.repuesto_el)
        self.producto.stock = 4
        self.producto.save(update_fields=["stock", "actualizado"])  # como un ingreso de mercadería
        self.producto.refresh_from_db()
        self.assertIsNotNone(self.producto.repuesto_el)

    def test_cambiar_el_stock_sin_estar_agotado_no_la_cambia(self):
        self.producto.stock = 9
        self.producto.save()
        self.producto.refresh_from_db()
        self.assertIsNone(self.producto.repuesto_el)


class OrdenRecomendadoTests(BaseFavoritos):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.cliente)
        ahora = timezone.now()

        def guardar(nombre, hace_dias, **datos):
            producto = self.crear_producto(nombre=nombre, **datos)
            favorito, _ = Favorito.guardar(self.cliente, producto)
            Favorito.objects.filter(pk=favorito.pk).update(creado=ahora - timedelta(days=hace_dias))
            return producto

        # «Galaxy A15» (self.producto) no está en favoritos.
        self.normal_viejo = guardar("Normal viejo", 20)
        self.normal_nuevo = guardar("Normal nuevo", 1)
        self.agotado = guardar("Agotado", 0, stock=0)
        self.rebajado = guardar("Rebajado", 15)
        self.rebajado.precio = Decimal("600.00")
        self.rebajado.save()
        self.repuesto = guardar("Repuesto", 10, stock=0)
        self.repuesto.stock = 2
        self.repuesto.save()
        self.repuesto_hace_tiempo = guardar("Repuesto hace tiempo", 30)
        Producto.objects.filter(pk=self.repuesto_hace_tiempo.pk).update(repuesto_el=ahora - timedelta(days=9))
        self.oculto = guardar("Retirado", 0)
        Producto.objects.filter(pk=self.oculto.pk).update(activo=False)

    def nombres(self, **parametros):
        respuesta = self.client.get(reverse("favoritos:lista"), parametros)
        return [f.producto.nombre for f in respuesta.context["pagina"]]

    def test_orden_por_grupos_y_el_ultimo_agregado_primero(self):
        self.assertEqual(self.nombres(), [
            "Rebajado",                                         # 1. bajó de precio
            "Repuesto",                                         # 2. volvió a tener stock (últimos 7 días)
            "Normal nuevo", "Normal viejo", "Repuesto hace tiempo",  # 3. los demás, del más reciente
            "Retirado", "Agotado",                              # 4. no disponibles y agotados
        ])

    def test_un_rebajado_pero_agotado_va_al_final(self):
        self.rebajado.stock = 0
        self.rebajado.save()
        self.assertEqual(self.nombres()[-1], "Rebajado")

    def test_la_reposicion_deja_de_contar_a_los_7_dias(self):
        Producto.objects.filter(pk=self.repuesto.pk).update(repuesto_el=timezone.now() - timedelta(days=8))
        self.assertEqual(self.nombres()[1:4], ["Normal nuevo", "Repuesto", "Normal viejo"])

    def test_texto_de_la_rebaja_sin_tercer_precio(self):
        respuesta = self.client.get(reverse("favoritos:lista"))
        self.assertContains(respuesta, "Bajó S/ 100.00 desde que lo guardaste", count=1)
        self.assertContains(respuesta, 'class="favorito-rebaja"')
        self.assertNotContains(respuesta, "Bajó de precio")

    def test_otros_ordenes_dejan_agotados_y_no_disponibles_al_final(self):
        self.assertEqual(self.nombres(orden="nombre")[:5],
                         ["Normal nuevo", "Normal viejo", "Rebajado", "Repuesto", "Repuesto hace tiempo"])
        self.assertEqual(set(self.nombres(orden="nombre")[5:]), {"Agotado", "Retirado"})
        self.assertEqual(self.nombres(orden="precio_asc")[0], "Rebajado")  # S/ 600 frente a S/ 700
        self.assertEqual(self.nombres(orden="recientes")[:2], ["Normal nuevo", "Repuesto"])

    def test_mayor_descuento(self):
        self.normal_viejo.precio_oferta = Decimal("490.00")  # -30 %
        self.normal_viejo.save()
        self.normal_nuevo.precio_oferta = Decimal("630.00")  # -10 %
        self.normal_nuevo.save()
        self.assertEqual(self.nombres(orden="descuento")[:2], ["Normal viejo", "Normal nuevo"])


class OrdenQueSeRecuerdaTests(BaseFavoritos):
    def setUp(self):
        super().setUp()
        Favorito.guardar(self.cliente, self.producto)
        self.client.force_login(self.cliente)

    def test_el_selector_aparece_con_recomendado_por_defecto(self):
        respuesta = self.client.get(reverse("favoritos:lista"))
        self.assertEqual(respuesta.context["orden"], "recomendado")
        self.assertContains(respuesta, 'name="orden" id="orden-favoritos"')
        self.assertContains(respuesta, '<option value="recomendado" selected>Recomendado</option>', html=True)
        self.assertContains(respuesta, "Mayor descuento")

    def test_la_eleccion_se_guarda_y_se_usa_la_proxima_vez(self):
        self.client.get(reverse("favoritos:lista"), {"orden": "precio_desc"})
        self.assertEqual(PreferenciaFavoritos.objects.get(usuario=self.cliente).orden, "precio_desc")
        respuesta = self.client.get(reverse("favoritos:lista"))
        self.assertEqual(respuesta.context["orden"], "precio_desc")
        self.assertContains(respuesta, '<option value="precio_desc" selected>Precio: mayor a menor</option>', html=True)

    def test_un_orden_inventado_no_se_guarda(self):
        respuesta = self.client.get(reverse("favoritos:lista"), {"orden": "cualquier_cosa"})
        self.assertEqual(respuesta.context["orden"], "recomendado")
        self.assertFalse(PreferenciaFavoritos.objects.exists())

    def test_cada_cliente_tiene_su_propio_orden(self):
        from .tests import crear_cliente

        self.client.get(reverse("favoritos:lista"), {"orden": "nombre"})
        otro = crear_cliente("cliente2")
        self.client.force_login(otro)
        self.assertEqual(self.client.get(reverse("favoritos:lista")).context["orden"], "recomendado")


class AgotadoNoEsNoDisponibleTests(BaseFavoritos):
    def setUp(self):
        super().setUp()
        Favorito.guardar(self.cliente, self.producto)
        self.producto.stock = 0
        self.producto.save()
        self.client.force_login(self.cliente)

    def test_favorito_agotado_pregunta_cuando_llega(self):
        respuesta = self.client.get(reverse("favoritos:lista"))
        self.assertContains(respuesta, "Agotado")
        self.assertNotContains(respuesta, "No disponible")
        self.assertContains(respuesta, "tarjeta-favorito--agotado")
        self.assertContains(respuesta, "¿Cuándo llega?")  # corto, para que entre en la tarjeta
        self.assertContains(respuesta, "https://wa.me/51911111111")  # la tienda sigue activa
        self.assertNotContains(respuesta, "</i> WhatsApp</a>")

    def test_el_mensaje_pregunta_cuando_vuelve_a_tener_stock(self):
        mensaje = self.producto.mensaje_whatsapp()
        self.assertIn("Vi este producto en NEXALYS Tec y aparece agotado:\n\n*Galaxy A15*", mensaje)
        self.assertIn("¿Saben cuándo vuelve a tener stock?", mensaje)
        self.assertNotIn("Precio:", mensaje)

    def test_la_pagina_del_producto_tambien(self):
        respuesta = self.client.get(reverse("catalogo:detalle", args=[self.producto.pk]))
        self.assertContains(respuesta, "Preguntar cuándo llega")
        self.assertContains(respuesta, "btn btn-outline-success btn-lg")
        self.assertNotContains(respuesta, "Consultar por WhatsApp")

    def test_con_stock_sigue_igual(self):
        self.producto.stock = 2
        self.producto.save()
        respuesta = self.client.get(reverse("favoritos:lista"))
        self.assertContains(respuesta, "</i> WhatsApp</a>")
        self.assertNotContains(respuesta, "¿Cuándo llega?")
        self.assertIn("¿Sigue disponible? ¿Cómo puedo comprarlo?", self.producto.mensaje_whatsapp())


class NoDisponibleExplicadoTests(BaseFavoritos):
    def setUp(self):
        super().setUp()
        Favorito.guardar(self.cliente, self.producto)
        self.client.force_login(self.cliente)

    def test_la_tienda_lo_oculto_se_explica_y_se_puede_ver_la_tienda(self):
        self.producto.activo = False
        self.producto.save()
        respuesta = self.client.get(reverse("favoritos:lista"))
        self.assertContains(respuesta, "No disponible")
        self.assertContains(respuesta, "La tienda ya no lo tiene publicado. Si lo vuelve a publicar, aparecerá aquí como antes.")
        self.assertContains(respuesta, "Ver tienda")
        self.assertContains(respuesta, f'href="{reverse("tiendas:perfil", args=[self.tienda.pk])}"')
        self.assertNotContains(respuesta, "https://wa.me/")

    def test_tienda_suspendida_sin_ver_tienda(self):
        self.tienda.suspender("Prueba")
        respuesta = self.client.get(reverse("favoritos:lista"))
        self.assertContains(respuesta, "Esta tienda no está disponible por ahora.")
        self.assertNotContains(respuesta, "Ver tienda")

    def test_al_publicarlo_de_nuevo_vuelve_a_estar_disponible_y_sube(self):
        otro = self.crear_producto(nombre="Otro")
        Favorito.guardar(self.cliente, otro)  # el más reciente: normalmente iría primero
        self.producto.activo = False
        self.producto.save()
        self.producto.activo = True
        self.producto.save()
        respuesta = self.client.get(reverse("favoritos:lista"))
        self.assertEqual([f.producto.nombre for f in respuesta.context["pagina"]], ["Galaxy A15", "Otro"])
        self.assertContains(respuesta, "Volvió a estar disponible")
        self.assertNotContains(respuesta, "Volvió a tener stock")

    def test_el_administrador_lo_muestra_de_nuevo(self):
        self.producto.oculto_por_admin = True
        self.producto.save(update_fields=["oculto_por_admin", "actualizado"])
        self.producto.oculto_por_admin = False
        self.producto.save(update_fields=["oculto_por_admin", "actualizado"])
        self.producto.refresh_from_db()
        self.assertIsNotNone(self.producto.republicado_el)

    def test_la_tienda_reactivada_vuelve_a_estar_disponible(self):
        self.tienda.verificada_en = timezone.now()
        self.tienda.save()
        self.tienda.suspender("Prueba")
        self.tienda.reactivar()
        self.assertContains(self.client.get(reverse("favoritos:lista")), "Volvió a estar disponible")

    def test_crear_o_editar_sin_ocultar_no_cuenta(self):
        self.producto.precio = Decimal("690.00")
        self.producto.save()
        self.producto.refresh_from_db()
        self.assertIsNone(self.producto.republicado_el)
