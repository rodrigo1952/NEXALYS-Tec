"""Pruebas de ofertas y productos destacados."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.urls import reverse
from django.utils import timezone

from favoritos.models import Favorito
from pedidos.models import Pedido
from pedidos.servicios import registrar_pedido

from .models import MAX_DESTACADOS, Producto
from .tests import BaseCatalogo

HOY = timezone.localdate


class OfertaModeloTests(BaseCatalogo):
    def test_oferta_vigente(self):
        producto = self.crear_producto(precio=Decimal("2799.00"), precio_oferta=Decimal("2499.00"))
        self.assertTrue(producto.en_oferta)
        self.assertEqual(producto.precio_final, Decimal("2499.00"))
        self.assertEqual(producto.porcentaje_descuento, 11)

    def test_oferta_vencida_vuelve_al_precio_normal(self):
        producto = self.crear_producto(
            precio=Decimal("2799.00"), precio_oferta=Decimal("2499.00"), oferta_hasta=HOY() - timedelta(days=1)
        )
        self.assertFalse(producto.en_oferta)
        self.assertEqual(producto.precio_final, Decimal("2799.00"))

    def test_el_ultimo_dia_la_oferta_sigue_vigente(self):
        producto = self.crear_producto(precio=Decimal("100"), precio_oferta=Decimal("80"), oferta_hasta=HOY())
        self.assertTrue(producto.en_oferta)

    def test_whatsapp_menciona_el_precio_de_oferta(self):
        producto = self.crear_producto(precio=Decimal("100.00"), precio_oferta=Decimal("80.00"))
        self.assertIn("S/ 80.00", producto.mensaje_whatsapp())

    def test_el_pedido_toma_el_precio_de_oferta(self):
        producto = self.crear_producto(precio=Decimal("100.00"), precio_oferta=Decimal("80.00"), stock=5)
        pedido = registrar_pedido(Pedido(
            tienda=self.tienda, producto=producto, cantidad=1,
            cliente_nombre="Ana Quispe", cliente_telefono="987654321",
        ))
        self.assertEqual(pedido.precio_unitario, Decimal("80.00"))


class OfertaFormularioTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.tienda.usuario)

    def crear(self, **cambios):
        return self.client.post(reverse("catalogo:crear"), self.datos_formulario(**cambios))

    def test_crear_producto_con_oferta(self):
        manana = (HOY() + timedelta(days=1)).isoformat()
        respuesta = self.crear(precio="899.00", precio_oferta="799.00", oferta_hasta=manana)
        self.assertRedirects(respuesta, reverse("catalogo:mis_productos"))
        self.assertTrue(Producto.objects.get().en_oferta)

    def test_oferta_mayor_o_igual_al_precio_se_rechaza(self):
        respuesta = self.crear(precio="899.00", precio_oferta="899.00")
        self.assertIn("precio_oferta", respuesta.context["form"].errors)

    def test_fecha_en_el_pasado_se_rechaza(self):
        ayer = (HOY() - timedelta(days=1)).isoformat()
        respuesta = self.crear(precio_oferta="799.00", oferta_hasta=ayer)
        self.assertIn("oferta_hasta", respuesta.context["form"].errors)

    def test_fecha_sin_precio_de_oferta_se_rechaza(self):
        manana = (HOY() + timedelta(days=1)).isoformat()
        respuesta = self.crear(oferta_hasta=manana)
        self.assertIn("oferta_hasta", respuesta.context["form"].errors)

    def test_oferta_vencida_no_impide_editar_lo_demas(self):
        ayer = HOY() - timedelta(days=1)
        producto = self.crear_producto(precio=Decimal("899.00"), precio_oferta=Decimal("799.00"), oferta_hasta=ayer)
        url = reverse("catalogo:editar", args=[producto.pk])
        version = self.client.get(url).context["form"]["version"].value()
        respuesta = self.client.post(url, self.datos_formulario(
            nombre="Galaxy A15", precio="899.00", precio_oferta="799.00", oferta_hasta=ayer.isoformat(),
            stock="20", version=version,
        ))
        self.assertRedirects(respuesta, reverse("catalogo:mis_productos"))
        producto.refresh_from_db()
        self.assertEqual(producto.stock, 20)

    def test_maximo_de_destacados_por_tienda(self):
        for numero in range(MAX_DESTACADOS):
            self.crear_producto(nombre=f"Destacado {numero}", destacado=True)
        respuesta = self.crear(destacado="on")
        self.assertIn("destacado", respuesta.context["form"].errors)

    def test_otra_tienda_no_cuenta_para_el_limite(self):
        for numero in range(MAX_DESTACADOS):
            self.crear_producto(tienda=self.otra_tienda, nombre=f"Ajeno {numero}", destacado=True)
        respuesta = self.crear(destacado="on")
        self.assertRedirects(respuesta, reverse("catalogo:mis_productos"))


class OfertaCatalogoTests(BaseCatalogo):
    def test_inicio_muestra_destacados_y_ofertas(self):
        self.crear_producto(nombre="Laptop destacada", destacado=True)
        self.crear_producto(nombre="Mouse en oferta", precio=Decimal("50"), precio_oferta=Decimal("40"))
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, "Productos destacados")
        self.assertContains(respuesta, "Laptop destacada")
        self.assertContains(respuesta, "Mouse en oferta")
        self.assertContains(respuesta, "-20%")

    def test_filtro_solo_ofertas(self):
        self.crear_producto(nombre="Teclado sin rebaja")
        self.crear_producto(nombre="Rebajado", precio=Decimal("50"), precio_oferta=Decimal("40"))
        respuesta = self.client.get(reverse("catalogo:catalogo"), {"solo_ofertas": "on"})
        self.assertContains(respuesta, "Rebajado")
        self.assertNotContains(respuesta, "Teclado sin rebaja")

    def test_ordenar_y_filtrar_por_el_precio_con_oferta(self):
        self.crear_producto(nombre="Caro rebajado", precio=Decimal("500"), precio_oferta=Decimal("90"))
        self.crear_producto(nombre="Barato normal", precio=Decimal("100"))
        respuesta = self.client.get(reverse("catalogo:catalogo"), {"orden": "precio_asc"})
        nombres = [p.nombre for p in respuesta.context["pagina"]]
        self.assertEqual(nombres, ["Caro rebajado", "Barato normal"])

        respuesta = self.client.get(reverse("catalogo:catalogo"), {"precio_max": "95"})
        self.assertContains(respuesta, "Caro rebajado")
        self.assertNotContains(respuesta, "Barato normal")

    def test_oferta_cuenta_como_baja_de_precio_en_favoritos(self):
        cliente = User.objects.create_user("cliente1", "c@ejemplo.com", "ClaveSegura#2026")
        cliente.groups.add(Group.objects.get(name="Cliente"))
        producto = self.crear_producto(precio=Decimal("100.00"))
        Favorito.guardar(cliente, producto)
        producto.precio_oferta = Decimal("80.00")
        producto.save()

        self.client.force_login(cliente)
        self.assertEqual(self.client.get(reverse("inicio")).context["avisos_favoritos"], 1)
        self.assertContains(self.client.get(reverse("favoritos:lista")), "Bajó de precio")
