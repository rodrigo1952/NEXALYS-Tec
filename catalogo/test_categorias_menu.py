"""Barra de categorías (las 5 con más movimiento) y tarjeta de producto sin «Ver detalle»."""

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from favoritos.models import Favorito
from tiendas.models import Tienda

from .context_processors import calcular_categorias
from .models import Categoria, VistaProducto
from .tests import BaseCatalogo


class BarraCategoriasTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.nombres = ["Audio", "Laptops", "Tablets", "Pantallas", "Repuestos", "Accesorios", "Otros"]
        self.cats = {n: Categoria.objects.get_or_create(nombre=n)[0] for n in self.nombres}
        self.productos = {}
        for n in self.nombres:
            self.productos[n] = self.crear_producto(nombre=f"Producto {n}", categoria=self.cats[n])

    def visitas(self, nombre, cantidad, dias_atras=0):
        fecha = timezone.localdate() - timedelta(days=dias_atras)
        for i in range(cantidad):
            VistaProducto.objects.create(producto=self.productos[nombre], visitante=f"s{nombre}{i}{dias_atras}", fecha=fecha)

    def nombres_principales(self):
        return [c.nombre for c in calcular_categorias()["principales"]]

    def test_las_principales_son_las_de_mas_movimiento(self):
        self.visitas("Repuestos", 4)
        self.visitas("Tablets", 2)
        cliente = self.crear_cliente()
        Favorito.objects.create(usuario=cliente, producto=self.productos["Accesorios"], precio_guardado=self.productos["Accesorios"].precio, precio_visto=self.productos["Accesorios"].precio)  # 1 favorito = 5 vistas
        principales = self.nombres_principales()
        self.assertEqual(principales[:3], ["Accesorios", "Repuestos", "Tablets"])
        self.assertEqual(len(principales), 5)

    def test_solo_cuentan_los_ultimos_30_dias(self):
        self.visitas("Pantallas", 10, dias_atras=40)
        self.visitas("Audio", 1)
        self.assertEqual(self.nombres_principales()[0], "Audio")

    def test_otros_nunca_es_principal_y_va_al_final_de_todas(self):
        self.visitas("Otros", 50)
        self.assertNotIn("Otros", self.nombres_principales())
        self.assertEqual(calcular_categorias()["todas"][-1].nombre, "Otros")

    def test_solo_categorias_con_productos_visibles(self):
        vacia = Categoria.objects.create(nombre="Drones")
        Tienda.objects.filter(pk=self.tienda.pk).update(estado=Tienda.Estado.SUSPENDIDA)
        self.crear_producto(tienda=self.otra_tienda, nombre="Galaxy visible")  # categoría Celulares
        todas = {c.nombre: c.cantidad for c in calcular_categorias()["todas"]}
        self.assertEqual(todas, {"Celulares": 1})
        self.assertNotIn(vacia.nombre, todas)

    def test_la_barra_aparece_en_las_paginas_y_marca_la_categoria_elegida(self):
        respuesta = self.client.get(reverse("catalogo:catalogo"), {"categoria": self.cats["Audio"].pk})
        self.assertContains(respuesta, 'class="barra-categorias"')
        self.assertContains(respuesta, "Todas<span")
        self.assertContains(respuesta, f'class="barra-categorias__enlace activa" aria-current="page" href="{reverse("catalogo:catalogo")}?categoria={self.cats["Audio"].pk}"')
        self.assertContains(self.client.get(reverse("inicio")), 'class="barra-categorias"')

    def test_no_aparece_en_iniciar_sesion(self):
        self.assertNotContains(self.client.get(reverse("login")), 'class="barra-categorias"')

    def crear_cliente(self):
        from django.contrib.auth.models import Group, User

        usuario = User.objects.create_user("cliente1", "c@ejemplo.com", "ClaveSegura#2026")
        usuario.groups.add(Group.objects.get_or_create(name="Cliente")[0])
        return usuario


class TarjetaProductoTests(BaseCatalogo):
    def test_el_nombre_lleva_al_detalle_y_no_hay_boton_ver_detalle(self):
        producto = self.crear_producto(nombre="Galaxy A55")
        respuesta = self.client.get(reverse("catalogo:catalogo"))
        self.assertNotContains(respuesta, "Ver detalle")
        self.assertContains(
            respuesta,
            f'<a href="{reverse("catalogo:detalle", args=[producto.pk])}" class="tarjeta-producto__nombre stretched-link">Galaxy A55</a>',
            html=True,
        )
        self.assertContains(respuesta, 'class="text-muted mt-auto tarjeta-producto__tienda"')
