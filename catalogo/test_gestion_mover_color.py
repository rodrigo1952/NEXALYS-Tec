"""
Nov 2026 (consola del administrador):
- Eliminar una categoría o marca con productos: primero pasan a otra y luego se elimina (queda en el Historial).
- 16 íconos nuevos para las categorías.
- Color de la etiqueta de cada marca, con revisión de contraste.
"""

from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.urls import reverse

from administracion.models import AccionAdmin

from .colores import COLOR_MARCA_POR_DEFECTO, contraste_con_blanco
from .models import ICONOS_CATEGORIA, Categoria, Marca, Producto
from .tests import BaseCatalogo


class BaseGestion(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user("jefe", "jefe@ejemplo.com", "ClaveSegura#2026")
        self.admin.groups.add(Group.objects.get(name="Administrador"))
        self.client.force_login(self.admin)

    def eliminar(self, tipo, registro, **datos):
        return self.client.post(reverse("catalogo:gestion_eliminar", args=[tipo, registro.pk]), datos)


class MoverYEliminarTests(BaseGestion):
    def test_categoria_con_productos_pasa_a_otra_y_se_elimina(self):
        vieja = Categoria.objects.create(nombre="Repuestos de celular")
        otros = Categoria.objects.get(nombre="Otros")
        uno = self.crear_producto(categoria=vieja, nombre="Pantalla A15")
        dos = self.crear_producto(categoria=vieja, nombre="Batería A15", tienda=self.otra_tienda)
        respuesta = self.client.get(reverse("catalogo:gestion_eliminar", args=["categorias", vieja.pk]))
        self.assertContains(respuesta, "Mover y eliminar")
        self.assertEqual(respuesta.context["num_tiendas"], 2)
        self.assertEqual(respuesta.context["form"]["destino"].value(), otros.pk)  # «Otros» viene marcado

        self.eliminar("categorias", vieja, destino=otros.pk)
        self.assertFalse(Categoria.objects.filter(pk=vieja.pk).exists())
        for producto in (uno, dos):
            producto.refresh_from_db()
            self.assertEqual(producto.categoria, otros)
            self.assertIn("otros", producto.etiquetas_busqueda)  # el buscador ya la encuentra en «Otros»
            self.assertNotIn("repuestos de celular", producto.etiquetas_busqueda)
        accion = AccionAdmin.objects.get(tipo=AccionAdmin.Tipo.ELIMINAR_CATEGORIA)
        self.assertEqual(accion.objetivo, "Categoría «Repuestos de celular»")
        self.assertIn("2 producto(s) pasaron a la categoría «Otros»", accion.motivo)

    def test_marca_con_productos_pasa_a_otra_y_se_elimina(self):
        vieja = Marca.objects.create(nombre="Genérica X")
        destino = Marca.objects.get(nombre="Xiaomi")
        producto = self.crear_producto(marca=vieja)
        self.eliminar("marcas", vieja, destino=destino.pk)
        self.assertFalse(Marca.objects.filter(pk=vieja.pk).exists())
        producto.refresh_from_db()
        self.assertEqual(producto.marca, destino)
        self.assertTrue(AccionAdmin.objects.filter(tipo=AccionAdmin.Tipo.ELIMINAR_MARCA, objetivo="Marca «Genérica X»").exists())

    def test_sin_elegir_destino_no_se_elimina(self):
        vieja = Categoria.objects.create(nombre="Drones")
        self.crear_producto(categoria=vieja)
        respuesta = self.eliminar("categorias", vieja)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(Categoria.objects.filter(pk=vieja.pk).exists())
        self.assertFalse(AccionAdmin.objects.exists())

    def test_no_se_puede_pasar_a_una_inactiva_ni_a_si_misma(self):
        vieja = Categoria.objects.create(nombre="Drones")
        apagada = Categoria.objects.create(nombre="Descontinuada", activa=False)
        self.crear_producto(categoria=vieja)
        respuesta = self.client.get(reverse("catalogo:gestion_eliminar", args=["categorias", vieja.pk]))
        opciones = list(respuesta.context["form"].fields["destino"].queryset)
        self.assertNotIn(apagada, opciones)
        self.assertNotIn(vieja, opciones)
        self.eliminar("categorias", vieja, destino=apagada.pk)
        self.assertTrue(Categoria.objects.filter(pk=vieja.pk).exists())

    def test_sin_productos_se_elimina_y_queda_en_el_historial(self):
        vieja = Marca.objects.create(nombre="Marca de prueba")
        self.eliminar("marcas", vieja)
        self.assertFalse(Marca.objects.filter(pk=vieja.pk).exists())
        self.assertEqual(AccionAdmin.objects.get().motivo, "No tenía productos.")


class IconosNuevosTests(BaseGestion):
    def test_hay_38_iconos_y_otros_va_al_final(self):
        valores = [valor for valor, _ in ICONOS_CATEGORIA]
        self.assertEqual(len(valores), 38)
        self.assertEqual(len(set(valores)), 38)
        self.assertEqual(valores[-1], "grid")
        for nuevo in ("projector", "mic", "webcam", "sim", "lightbulb", "gpu-card", "memory", "device-ssd",
                      "motherboard", "fan", "house-gear", "pen", "earbuds", "battery-full", "soundwave", "disc"):
            self.assertIn(nuevo, valores)

    def test_todos_los_iconos_existen_en_bootstrap_icons(self):
        from django.contrib.staticfiles import finders

        with open(finders.find("vendor/bootstrap-icons/bootstrap-icons.min.css"), encoding="utf-8") as archivo:
            css = archivo.read()
        for valor, nombre in ICONOS_CATEGORIA:
            self.assertIn(f".bi-{valor}::before", css, nombre)

    def test_crear_categoria_con_icono_nuevo(self):
        self.client.post(reverse("catalogo:gestion_crear", args=["categorias"]),
                         {"nombre": "Proyectores", "icono": "projector", "activa": "on"})
        self.assertEqual(Categoria.objects.get(nombre="Proyectores").icono, "projector")


class ColorDeMarcaTests(BaseGestion):
    def test_crear_marca_con_su_color(self):
        self.client.post(reverse("catalogo:gestion_crear", args=["marcas"]),
                         {"nombre": "Pioneer", "color": "#c8102e", "activa": "on"})
        self.assertEqual(Marca.objects.get(nombre="Pioneer").color, "#C8102E")

    def test_sin_color_queda_el_azul_marino(self):
        self.client.post(reverse("catalogo:gestion_crear", args=["marcas"]), {"nombre": "Pioneer", "activa": "on"})
        self.assertEqual(Marca.objects.get(nombre="Pioneer").color, COLOR_MARCA_POR_DEFECTO)

    def test_color_claro_se_rechaza_porque_no_se_lee(self):
        respuesta = self.client.post(reverse("catalogo:gestion_crear", args=["marcas"]),
                                     {"nombre": "Pioneer", "color": "#FFD400", "activa": "on"})
        self.assertIn("no se lee bien", respuesta.context["form"].errors["color"][0])
        self.assertFalse(Marca.objects.filter(nombre="Pioneer").exists())

    def test_color_mal_escrito_se_rechaza(self):
        respuesta = self.client.post(reverse("catalogo:gestion_crear", args=["marcas"]),
                                     {"nombre": "Pioneer", "color": "rojo", "activa": "on"})
        self.assertIn("color", respuesta.context["form"].errors)

    def test_formulario_con_selector_y_vista_previa(self):
        respuesta = self.client.get(reverse("catalogo:gestion_editar", args=["marcas", self.marca.pk]))
        self.assertContains(respuesta, 'type="color"')
        self.assertContains(respuesta, 'value="#1428A0"')
        self.assertContains(respuesta, "data-vista-marca")
        self.assertContains(respuesta, "js/color_marca.js")

    def test_la_tarjeta_y_la_lista_usan_el_color_guardado(self):
        Marca.objects.filter(pk=self.marca.pk).update(color="#2E7D32")
        self.crear_producto()
        html = self.client.get(reverse("catalogo:catalogo")).content.decode()
        self.assertIn('style="--chip-marca: #2E7D32">Samsung</span>', html)
        lista = self.client.get(reverse("catalogo:gestion_lista", args=["marcas"]), {"q": "sams"})
        self.assertContains(lista, 'style="--chip-marca: #2E7D32">Samsung</span>')

    def test_los_colores_que_ya_existian_se_leen_bien(self):
        for nombre, color in Marca.objects.values_list("nombre", "color"):
            self.assertGreaterEqual(contraste_con_blanco(color), 4.5, nombre)
