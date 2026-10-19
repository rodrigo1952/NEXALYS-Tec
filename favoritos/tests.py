"""
Pruebas de favoritos (Etapa 1 del perfil del cliente).
Ejecutar con:  python manage.py test favoritos
"""

from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, Marca, Producto
from tiendas.models import Tienda
from tiendas.tests import crear_tienda

from .models import Favorito

CLAVE = "ClaveSegura#2026"


def crear_cliente(usuario="cliente1"):
    user = User.objects.create_user(usuario, f"{usuario}@ejemplo.com", CLAVE)
    user.groups.add(Group.objects.get(name="Cliente"))
    return user


class BaseFavoritos(TestCase):
    def setUp(self):
        self.categoria, _ = Categoria.objects.get_or_create(nombre="Celulares")
        self.otra_categoria, _ = Categoria.objects.get_or_create(nombre="Laptops")
        self.marca, _ = Marca.objects.get_or_create(nombre="Samsung")
        self.tienda = crear_tienda("tienda1", "Tienda Uno", "911111111")
        self.otra_tienda = crear_tienda("tienda2", "Tienda Dos", "922222222")
        self.producto = self.crear_producto()
        self.cliente = crear_cliente()

    def crear_producto(self, tienda=None, **datos):
        valores = {
            "tienda": tienda or self.tienda,
            "categoria": self.categoria,
            "marca": self.marca,
            "nombre": "Galaxy A15",
            "precio": Decimal("700.00"),
            "stock": 5,
        }
        valores.update(datos)
        return Producto.objects.create(**valores)

    def alternar(self, producto=None):
        return self.client.post(reverse("favoritos:alternar", args=[(producto or self.producto).pk]))


class GuardarFavoritosTests(BaseFavoritos):
    def test_cliente_guarda_y_quita_con_el_corazon(self):
        self.client.force_login(self.cliente)
        self.alternar()
        self.assertTrue(Favorito.objects.filter(usuario=self.cliente, producto=self.producto).exists())
        self.alternar()
        self.assertFalse(Favorito.objects.filter(usuario=self.cliente, producto=self.producto).exists())

    def test_guarda_el_precio_del_momento(self):
        favorito, _ = Favorito.guardar(self.cliente, self.producto)
        self.assertEqual(favorito.precio_guardado, Decimal("700.00"))

    def test_no_se_duplica(self):
        Favorito.guardar(self.cliente, self.producto)
        Favorito.guardar(self.cliente, self.producto)
        self.assertEqual(Favorito.objects.filter(usuario=self.cliente).count(), 1)

    def test_tienda_no_puede_tener_favoritos(self):
        self.client.force_login(self.tienda.usuario)
        self.assertEqual(self.alternar().status_code, 403)
        self.assertEqual(self.client.get(reverse("favoritos:lista")).status_code, 403)

    def test_no_se_guarda_un_producto_oculto(self):
        oculto = self.crear_producto(nombre="Oculto", activo=False)
        self.client.force_login(self.cliente)
        self.assertEqual(self.alternar(oculto).status_code, 404)

    def test_el_corazon_no_acepta_get(self):
        self.client.force_login(self.cliente)
        respuesta = self.client.get(reverse("favoritos:alternar", args=[self.producto.pk]))
        self.assertEqual(respuesta.status_code, 405)

    def test_vuelve_a_la_pagina_de_origen(self):
        self.client.force_login(self.cliente)
        origen = reverse("catalogo:catalogo") + "?q=galaxy"
        respuesta = self.client.post(
            reverse("favoritos:alternar", args=[self.producto.pk]), {"next": origen}
        )
        self.assertRedirects(respuesta, origen)

    def test_no_redirige_a_otro_sitio(self):
        self.client.force_login(self.cliente)
        respuesta = self.client.post(
            reverse("favoritos:alternar", args=[self.producto.pk]), {"next": "https://malicioso.com/"}
        )
        self.assertRedirects(respuesta, reverse("favoritos:lista"))

    def test_eliminar_el_producto_borra_el_favorito(self):
        Favorito.guardar(self.cliente, self.producto)
        self.producto.delete()
        self.assertFalse(Favorito.objects.exists())


class VisitanteTests(BaseFavoritos):
    def test_visitante_va_al_login_y_se_guarda_al_entrar(self):
        respuesta = self.client.get(reverse("favoritos:guardar_despues", args=[self.producto.pk]))
        detalle = reverse("catalogo:detalle", args=[self.producto.pk])
        self.assertRedirects(respuesta, f"{reverse('login')}?next={detalle}", fetch_redirect_response=False)
        self.assertFalse(Favorito.objects.exists())

        self.client.post(reverse("login"), {"username": "cliente1", "password": CLAVE, "next": detalle})
        self.assertTrue(Favorito.objects.filter(usuario=self.cliente, producto=self.producto).exists())

    def test_si_entra_una_tienda_no_se_guarda(self):
        self.client.get(reverse("favoritos:guardar_despues", args=[self.producto.pk]))
        self.client.post(reverse("login"), {"username": "tienda1", "password": CLAVE})
        self.assertFalse(Favorito.objects.exists())

    def test_visitante_ve_el_corazon_que_lleva_al_login(self):
        respuesta = self.client.get(reverse("catalogo:catalogo"))
        self.assertContains(respuesta, reverse("favoritos:guardar_despues", args=[self.producto.pk]))

    def test_tienda_no_ve_el_corazon(self):
        self.client.force_login(self.tienda.usuario)
        respuesta = self.client.get(reverse("catalogo:catalogo"))
        self.assertNotContains(respuesta, reverse("favoritos:alternar", args=[self.producto.pk]))
        self.assertNotContains(respuesta, reverse("favoritos:guardar_despues", args=[self.producto.pk]))


class ListaFavoritosTests(BaseFavoritos):
    def test_lista_muestra_solo_mis_favoritos(self):
        otro = crear_cliente("cliente2")
        ajeno = self.crear_producto(nombre="Producto ajeno")
        Favorito.guardar(self.cliente, self.producto)
        Favorito.guardar(otro, ajeno)
        self.client.force_login(self.cliente)
        respuesta = self.client.get(reverse("favoritos:lista"))
        self.assertContains(respuesta, "Galaxy A15")
        self.assertNotContains(respuesta, "Producto ajeno")

    def test_lista_tiene_whatsapp_y_quitar(self):
        Favorito.guardar(self.cliente, self.producto)
        self.client.force_login(self.cliente)
        respuesta = self.client.get(reverse("favoritos:lista"))
        self.assertContains(respuesta, "https://wa.me/51911111111")
        self.assertContains(respuesta, reverse("favoritos:alternar", args=[self.producto.pk]))

    def test_filtrar_por_tienda_y_categoria(self):
        de_otra_tienda = self.crear_producto(tienda=self.otra_tienda, nombre="Laptop X", categoria=self.otra_categoria)
        Favorito.guardar(self.cliente, self.producto)
        Favorito.guardar(self.cliente, de_otra_tienda)
        self.client.force_login(self.cliente)

        respuesta = self.client.get(reverse("favoritos:lista"), {"tienda": self.otra_tienda.pk})
        self.assertContains(respuesta, "Laptop X")
        self.assertNotContains(respuesta, "Galaxy A15")

        respuesta = self.client.get(reverse("favoritos:lista"), {"categoria": self.categoria.pk})
        self.assertContains(respuesta, "Galaxy A15")
        self.assertNotContains(respuesta, "Laptop X")

    def test_filtro_invalido_no_rompe_la_pagina(self):
        self.client.force_login(self.cliente)
        respuesta = self.client.get(reverse("favoritos:lista"), {"tienda": "abc"})
        self.assertEqual(respuesta.status_code, 200)

    def test_producto_oculto_o_tienda_suspendida_se_muestra_no_disponible(self):
        Favorito.guardar(self.cliente, self.producto)
        self.tienda.estado = Tienda.Estado.SUSPENDIDA
        self.tienda.save()
        self.client.force_login(self.cliente)
        respuesta = self.client.get(reverse("favoritos:lista"))
        self.assertContains(respuesta, "No disponible")
        self.assertNotContains(respuesta, "https://wa.me/51911111111")
        self.assertTrue(Favorito.objects.exists())  # no se borra


class AvisosTests(BaseFavoritos):
    def avisos(self):
        return self.client.get(reverse("inicio")).context["avisos_favoritos"]

    def test_bajo_de_precio_muestra_etiqueta_y_contador(self):
        Favorito.guardar(self.cliente, self.producto)
        self.producto.precio = Decimal("650.00")
        self.producto.save()
        self.client.force_login(self.cliente)

        self.assertEqual(self.avisos(), 1)
        respuesta = self.client.get(reverse("favoritos:lista"))
        self.assertContains(respuesta, "Bajó de precio")
        self.assertContains(respuesta, "700.00")  # precio al guardarlo, tachado

        # Después de verlo, el contador baja, pero la etiqueta sigue
        # porque el precio aún es menor que cuando lo guardó.
        self.assertEqual(self.avisos(), 0)
        self.assertContains(self.client.get(reverse("favoritos:lista")), "Bajó de precio")

    def test_subir_de_precio_no_avisa(self):
        Favorito.guardar(self.cliente, self.producto)
        self.producto.precio = Decimal("750.00")
        self.producto.save()
        self.client.force_login(self.cliente)
        self.assertEqual(self.avisos(), 0)
        self.assertNotContains(self.client.get(reverse("favoritos:lista")), "Bajó de precio")

    def test_volvio_a_tener_stock_avisa_una_vez(self):
        self.producto.stock = 0
        self.producto.save()
        Favorito.guardar(self.cliente, self.producto)
        self.producto.stock = 3
        self.producto.save()
        self.client.force_login(self.cliente)

        self.assertEqual(self.avisos(), 1)
        self.assertContains(self.client.get(reverse("favoritos:lista")), "Volvió a tener stock")
        self.assertEqual(self.avisos(), 0)
        self.assertNotContains(self.client.get(reverse("favoritos:lista")), "Volvió a tener stock")

    def test_menu_muestra_mis_favoritos_al_cliente(self):
        self.client.force_login(self.cliente)
        self.assertContains(self.client.get(reverse("inicio")), reverse("favoritos:lista"))


class ConteoParaTiendaTests(BaseFavoritos):
    def test_tienda_ve_cuantos_lo_guardaron_pero_no_quienes(self):
        Favorito.guardar(self.cliente, self.producto)
        Favorito.guardar(crear_cliente("cliente2"), self.producto)
        self.client.force_login(self.tienda.usuario)

        respuesta = self.client.get(reverse("catalogo:mis_productos"))
        self.assertEqual(respuesta.context["pagina"][0].num_favoritos, 2)
        self.assertNotContains(respuesta, "cliente1")

        panel = self.client.get(reverse("tiendas:panel"))
        self.assertContains(panel, "2 personas")
        self.assertNotContains(panel, "cliente2")


class CorazonSinRecargarTests(BaseFavoritos):
    """El corazón responde con JSON cuando lo envía el JavaScript (la página no salta arriba)."""

    def alternar_js(self):
        return self.client.post(
            reverse("favoritos:alternar", args=[self.producto.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def test_guardar_y_quitar_responde_json(self):
        self.client.force_login(self.cliente)
        respuesta = self.alternar_js()
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()["guardado"])
        self.assertIn("Guardaste", respuesta.json()["mensaje"])
        self.assertTrue(Favorito.objects.filter(usuario=self.cliente, producto=self.producto).exists())

        respuesta = self.alternar_js()
        self.assertFalse(respuesta.json()["guardado"])
        self.assertFalse(Favorito.objects.filter(usuario=self.cliente, producto=self.producto).exists())

    def test_con_json_no_quedan_mensajes_pendientes(self):
        # Si quedara el mensaje, aparecería repetido al cambiar de página.
        self.client.force_login(self.cliente)
        self.alternar_js()
        respuesta = self.client.get(reverse("inicio"))
        self.assertNotContains(respuesta, "Guardaste")

    def test_sin_javascript_sigue_redirigiendo(self):
        self.client.force_login(self.cliente)
        respuesta = self.alternar()
        self.assertEqual(respuesta.status_code, 302)

    def test_el_boton_lleva_la_marca_para_el_javascript(self):
        self.client.force_login(self.cliente)
        respuesta = self.client.get(reverse("catalogo:detalle", args=[self.producto.pk]))
        self.assertContains(respuesta, f'data-favorito="{self.producto.pk}"')
        self.assertContains(respuesta, 'id="aviso-favorito"')
