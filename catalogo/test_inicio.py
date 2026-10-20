"""Etapa 5: orden de Destacados (popularidad) y Ofertas (mayor descuento) en Inicio."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.urls import reverse
from django.utils import timezone

from favoritos.models import Favorito

from .models import Producto, VistaProducto
from .tests import BaseCatalogo


def crear_cliente(usuario):
    user = User.objects.create_user(usuario, f"{usuario}@ejemplo.com", "ClaveSegura#2026")
    user.groups.add(Group.objects.get(name="Cliente"))
    return user


class DestacadoDesdeTests(BaseCatalogo):
    def test_se_guarda_al_destacar_y_se_borra_al_quitar(self):
        producto = self.crear_producto(destacado=True)
        self.assertIsNotNone(producto.destacado_desde)
        producto.destacado = False
        producto.save()
        self.assertIsNone(producto.destacado_desde)

    def test_volver_a_guardar_no_cambia_la_fecha(self):
        producto = self.crear_producto(destacado=True)
        fecha = producto.destacado_desde
        producto.stock = 2
        producto.save()
        self.assertEqual(producto.destacado_desde, fecha)


class VistasTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.producto = self.crear_producto()
        self.url = reverse("catalogo:detalle", args=[self.producto.pk])

    def test_una_vista_por_visitante_al_dia(self):
        for _ in range(5):
            self.client.get(self.url)  # visitante sin cuenta recargando
        self.assertEqual(VistaProducto.objects.count(), 1)
        self.client.force_login(crear_cliente("cliente1"))
        self.client.get(self.url)
        self.client.get(self.url)
        self.assertEqual(VistaProducto.objects.count(), 2)

    def test_no_cuentan_la_propia_tienda_ni_el_admin(self):
        self.client.force_login(self.tienda.usuario)
        self.client.get(self.url)
        self.client.force_login(User.objects.create_superuser("admin", "a@ejemplo.com", "ClaveSegura#2026"))
        self.client.get(self.url)
        self.assertFalse(VistaProducto.objects.exists())

    def test_la_tienda_no_ve_el_numero_de_vistas(self):
        self.client.get(self.url)
        self.client.force_login(self.tienda.usuario)
        respuesta = self.client.get(reverse("catalogo:mis_productos"))
        self.assertNotContains(respuesta, "Vistas")


class OrdenDestacadosTests(BaseCatalogo):
    def destacados(self):
        respuesta = self.client.get(reverse("inicio"))
        return [p.nombre for p in respuesta.context["destacados"]]

    def test_favoritos_pesan_mas_que_vistas(self):
        mirado = self.crear_producto(nombre="Muy mirado", destacado=True)
        guardado = self.crear_producto(nombre="Guardado", destacado=True)
        for i in range(4):  # 4 vistas = 4 puntos
            VistaProducto.objects.create(producto=mirado, visitante=f"s{i}")
        Favorito.guardar(crear_cliente("cliente1"), guardado)  # 1 favorito = 5 puntos
        self.assertEqual(self.destacados()[:2], ["Guardado", "Muy mirado"])

    def test_mas_vistas_va_primero(self):
        poco = self.crear_producto(nombre="Poco visto", destacado=True)
        mucho = self.crear_producto(nombre="Muy visto", destacado=True)
        VistaProducto.objects.create(producto=poco, visitante="s1")
        for i in range(3):
            VistaProducto.objects.create(producto=mucho, visitante=f"s{i}")
        self.assertEqual(self.destacados()[:2], ["Muy visto", "Poco visto"])

    def test_empate_gana_el_que_se_destaco_antes(self):
        nuevo = self.crear_producto(nombre="Destacado hoy", destacado=True)
        antiguo = self.crear_producto(nombre="Destacado hace días", destacado=True)
        Producto.objects.filter(pk=antiguo.pk).update(destacado_desde=timezone.now() - timedelta(days=5))
        self.assertEqual(self.destacados()[:2], ["Destacado hace días", "Destacado hoy"])

    def test_solo_cuentan_los_ultimos_30_dias(self):
        viejo = self.crear_producto(nombre="Popular hace meses", destacado=True)
        actual = self.crear_producto(nombre="Popular ahora", destacado=True)
        hace_meses = timezone.localdate() - timedelta(days=60)
        for i in range(10):
            VistaProducto.objects.create(producto=viejo, visitante=f"s{i}", fecha=hace_meses)
        VistaProducto.objects.create(producto=actual, visitante="s1")
        self.assertEqual(self.destacados()[0], "Popular ahora")

    def test_solo_aparecen_los_destacados(self):
        self.crear_producto(nombre="Normal")
        self.crear_producto(nombre="Estrella", destacado=True)
        self.assertEqual(self.destacados(), ["Estrella"])


class OrdenOfertasTests(BaseCatalogo):
    def test_mayor_descuento_primero(self):
        self.crear_producto(nombre="Diez por ciento", precio=Decimal("100.00"), precio_oferta=Decimal("90.00"))
        self.crear_producto(nombre="Mitad de precio", precio=Decimal("1000.00"), precio_oferta=Decimal("500.00"))
        self.crear_producto(nombre="Veinte por ciento", precio=Decimal("50.00"), precio_oferta=Decimal("40.00"))
        respuesta = self.client.get(reverse("inicio"))
        nombres = [p.nombre for p in respuesta.context["ofertas"]]
        self.assertEqual(nombres, ["Mitad de precio", "Veinte por ciento", "Diez por ciento"])
