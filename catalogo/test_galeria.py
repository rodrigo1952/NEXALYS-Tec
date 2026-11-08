"""Galería de fotos al editar un producto: un botón para cada cambio, aplicados al guardar."""

import os
import shutil
import tempfile

from django.test import override_settings
from django.urls import reverse
from PIL import Image

from .models import FotoProducto, Producto
from .test_fotos import foto
from .tests import BaseCatalogo

CARPETA_MEDIA = tempfile.mkdtemp()


def color(campo):
    """Color dominante del centro de la imagen guardada ("rojo" o "verde")."""
    with campo.storage.open(campo.name, "rb") as archivo:
        r, g, _ = Image.open(archivo).convert("RGB").getpixel((5, 5))
    return "rojo" if r > g else "verde"


def galeria_js():
    """Código de la galería (static/js/galeria_producto.js): ahí se dibujan las tarjetas."""
    from django.contrib.staticfiles import finders

    with open(finders.find("js/galeria_producto.js"), encoding="utf-8") as archivo:
        return archivo.read()


@override_settings(MEDIA_ROOT=CARPETA_MEDIA)
class GaleriaEdicionTests(BaseCatalogo):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.client.force_login(self.tienda.usuario)
        self.producto = self.crear_producto(imagen=foto("principal.png", color="red"))
        self.adicional = FotoProducto.objects.create(producto=self.producto, imagen=foto("extra.png"), orden=1)
        self.url = reverse("catalogo:editar", args=[self.producto.pk])

    def guardar(self, **cambios):
        version = self.client.get(self.url).context["form"]["version"].value()
        datos = self.datos_formulario(nombre="Galaxy A15", version=version)
        datos.update(cambios)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.url, datos)

    def test_la_galeria_muestra_todas_las_fotos_con_sus_botones(self):
        respuesta = self.client.get(self.url)
        for texto in ("Fotos del producto", "+ Agregar fotos", 'data-maximo="6"', 'name="galeria_plan"',
                      'id="fotos-actuales"', "js/galeria_producto.js"):
            self.assertContains(respuesta, texto)
        # Las fotos actuales, en orden (la principal primero), van a la galería con su ficha.
        self.assertEqual(respuesta.context["form"].fotos_galeria(), [
            {"ficha": "p", "url": self.producto.imagen.url},
            {"ficha": f"f{self.adicional.pk}", "url": self.adicional.imagen.url},
        ])
        for texto in ("Foto principal", "Cambiar foto principal", '"Hacer principal"', '"Reemplazar"', "Quitar la foto ",
                      "Agregar fotos", "arrástralas aquí", "Mover a la izquierda", "Mover a la derecha"):
            self.assertIn(texto, galeria_js())

    def test_la_galeria_mide_lo_mismo_con_pocas_o_muchas_fotos(self):
        # Principal arriba con alto fijo; debajo, siempre 5 casillas (las vacías con «+»).
        codigo = galeria_js()
        self.assertIn("for (var k = Math.max(fotos.length, 1); k < MAXIMO; k++) cajaSecundarias.appendChild(casillaVacia(", codigo)
        self.assertIn('botonIcono("bi-star-fill", "Hacer principal"', codigo)
        from django.contrib.staticfiles import finders

        with open(finders.find("css/marca.css"), encoding="utf-8") as archivo:
            css = archivo.read()
        self.assertIn(".tarjeta-foto--principal .tarjeta-foto__imagen { height: 300px; }", css)
        self.assertIn(".galeria-edicion__secundarias { grid-template-columns: repeat(5, minmax(0, 1fr)); }", css)

    def test_categoria_y_marca_en_una_fila(self):
        html = self.client.get(reverse("catalogo:crear")).content.decode()
        fila = html.index('<div class="row g-3 mb-3">')
        self.assertLess(fila, html.index('name="categoria"'))
        self.assertLess(html.index('name="categoria"'), html.index('name="marca"'))
        self.assertLess(html.index('name="marca"'), html.index('name="codigo"'))

    def test_hacer_principal_intercambia_las_fotos(self):
        respuesta = self.guardar(principal_foto=str(self.adicional.pk))
        self.assertRedirects(respuesta, reverse("catalogo:mis_productos") + f"#producto-{self.producto.pk}", fetch_redirect_response=False)
        self.producto.refresh_from_db()
        self.adicional.refresh_from_db()
        # La principal era roja y la adicional verde: ahora es al revés.
        self.assertEqual(color(self.producto.imagen), "verde")
        self.assertEqual(color(self.adicional.imagen), "rojo")
        self.assertTrue(self.producto.imagen.storage.exists(self.producto.imagen.name))
        self.assertTrue(self.adicional.imagen.storage.exists(self.adicional.imagen.name))
        self.assertNotEqual(self.producto.imagen.name, self.adicional.imagen.name)

    def test_hacer_principal_sin_foto_principal(self):
        Producto.objects.filter(pk=self.producto.pk).update(imagen="")
        self.guardar(principal_foto=str(self.adicional.pk))
        self.producto.refresh_from_db()
        self.assertTrue(self.producto.imagen.name)
        self.assertFalse(self.producto.fotos.exists())  # la adicional subió a principal
        self.assertTrue(self.producto.imagen.storage.exists(self.producto.imagen.name))

    def test_reemplazar_una_foto_adicional(self):
        anterior = self.adicional.imagen.path
        self.guardar(**{f"reemplazar_{self.adicional.pk}": foto("nueva.png", color="blue")})
        self.adicional.refresh_from_db()
        self.assertNotEqual(self.adicional.imagen.path, anterior)
        self.assertFalse(os.path.exists(anterior))  # el archivo viejo se borró

    def test_quitar_la_foto_principal(self):
        self.guardar(**{"imagen-clear": "on"})
        self.producto.refresh_from_db()
        self.assertFalse(self.producto.imagen)

    def test_no_se_puede_quitar_y_hacer_principal_a_la_vez(self):
        respuesta = self.guardar(principal_foto=str(self.adicional.pk), eliminar_fotos=[self.adicional.pk])
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No puedes quitar la foto que elegiste como principal")

    def test_agregar_fotos_al_editar(self):
        self.guardar(fotos_nuevas=[foto("a.png"), foto("b.png")])
        self.assertEqual(self.producto.fotos.count(), 3)

    def test_la_galeria_va_arriba_del_formulario(self):
        for url in (self.url, reverse("catalogo:crear")):
            html = self.client.get(url).content.decode()
            self.assertLess(html.index("data-galeria"), html.index('name="nombre"'))
            self.assertLess(html.index("data-principal"), html.index("data-secundarias"))

    def test_arrastrar_y_quitar_con_x(self):
        codigo = galeria_js()
        self.assertIn("img.draggable = true", codigo)  # todas las fotos se arrastran, también las nuevas
        for texto in ("Suelta para que sea la foto principal", "Suelta para cambiarlas de lugar", "zona-agregar", "tarjeta-foto__x"):
            self.assertIn(texto, codigo)
        self.assertNotContains(self.client.get(self.url), "modal-quitar-foto")  # la X no pide confirmación: se deshace

    def test_sin_espacio_no_hay_zona_para_agregar(self):
        for orden in range(2, 6):
            FotoProducto.objects.create(producto=self.producto, imagen=foto(f"extra{orden}.png"), orden=orden)
        formulario = self.client.get(self.url).context["form"]
        self.assertEqual(len(formulario.fotos_galeria()), formulario.fotos_maximo())
        self.assertIn("var hayLugar = fotos.length < MAXIMO;", galeria_js())

    def test_el_visor_recorre_las_fotos_del_producto(self):
        respuesta = self.client.get(reverse("catalogo:detalle", args=[self.producto.pk]))
        self.assertContains(respuesta, 'data-galeria="producto"', count=2)
        for parte in ('id="visor-anterior"', 'id="visor-siguiente"', 'id="visor-contador"'):
            self.assertContains(respuesta, parte)


@override_settings(MEDIA_ROOT=CARPETA_MEDIA)
class OrdenDeFotosTests(BaseCatalogo):
    """Las fotos adicionales se intercambian de lugar arrastrándolas y llevan un número de orden."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.tienda.usuario)
        self.producto = self.crear_producto(imagen=foto("principal.png", color="red"))
        self.f1, self.f2, self.f3 = (
            FotoProducto.objects.create(producto=self.producto, imagen=foto(f"extra{n}.png"), orden=n) for n in (1, 2, 3))
        self.url = reverse("catalogo:editar", args=[self.producto.pk])

    def guardar(self, **cambios):
        version = self.client.get(self.url).context["form"]["version"].value()
        datos = self.datos_formulario(nombre="Galaxy A15", version=version)
        datos.update(cambios)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.url, datos)

    def orden(self):
        return list(self.producto.fotos.values_list("pk", flat=True))

    def test_cada_foto_muestra_su_numero(self):
        self.assertContains(self.client.get(self.url), 'name="orden_fotos"')
        codigo = galeria_js()
        self.assertIn('<span class="numero-foto" title="Se ve primero">1</span>', codigo)
        self.assertIn('"numero-foto numero-foto--secundaria", String(i + 1)', codigo)

    def test_la_principal_tambien_se_arrastra(self):
        self.assertIn('img.alt = principal ? "Foto principal"', galeria_js())
        # La principal soltada sobre una adicional las intercambia (lo mismo que «Hacer principal»).
        respuesta = self.guardar(principal_foto=str(self.f2.pk))
        self.assertRedirects(respuesta, reverse("catalogo:mis_productos") + f"#producto-{self.producto.pk}", fetch_redirect_response=False)
        self.producto.refresh_from_db()
        self.f2.refresh_from_db()
        self.assertEqual(color(self.f2.imagen), "rojo")

    def test_guardar_el_nuevo_orden(self):
        respuesta = self.guardar(orden_fotos=f"{self.f3.pk},{self.f1.pk},{self.f2.pk}")
        self.assertRedirects(respuesta, reverse("catalogo:mis_productos") + f"#producto-{self.producto.pk}", fetch_redirect_response=False)
        self.assertEqual(self.orden(), [self.f3.pk, self.f1.pk, self.f2.pk])

    def test_ids_ajenos_o_repetidos_se_ignoran(self):
        ajena = FotoProducto.objects.create(producto=self.crear_producto(nombre="Otro"), imagen=foto("x.png"), orden=1)
        self.guardar(orden_fotos=f"{ajena.pk},{self.f2.pk},{self.f2.pk},abc")
        self.assertEqual(self.orden(), [self.f2.pk, self.f1.pk, self.f3.pk])  # las que faltan van al final
        ajena.refresh_from_db()
        self.assertEqual(ajena.orden, 1)

    def test_sin_cambios_no_se_toca_el_orden(self):
        self.guardar(orden_fotos="")
        self.assertEqual(self.orden(), [self.f1.pk, self.f2.pk, self.f3.pk])

    def test_las_fotos_nuevas_van_despues(self):
        self.guardar(orden_fotos=f"{self.f2.pk},{self.f1.pk},{self.f3.pk}", fotos_nuevas=[foto("nueva.png")])
        orden = self.orden()
        self.assertEqual(orden[:3], [self.f2.pk, self.f1.pk, self.f3.pk])
        self.assertEqual(len(orden), 4)

    def test_el_cliente_ve_las_fotos_en_ese_orden(self):
        self.guardar(orden_fotos=f"{self.f3.pk},{self.f1.pk},{self.f2.pk}")
        html = self.client.get(reverse("catalogo:detalle", args=[self.producto.pk])).content.decode()
        self.f1.refresh_from_db(); self.f2.refresh_from_db(); self.f3.refresh_from_db()
        posiciones = [html.index(f.imagen.url) for f in (self.f3, self.f1, self.f2)]
        self.assertEqual(posiciones, sorted(posiciones))


@override_settings(MEDIA_ROOT=CARPETA_MEDIA)
class CarruselAutomaticoTests(BaseCatalogo):
    def test_las_fotos_cambian_solas_cada_5_segundos_y_la_miniatura_se_resalta(self):
        producto = self.crear_producto(imagen=foto("principal.png"))
        FotoProducto.objects.create(producto=producto, imagen=foto("extra.png"), orden=1)
        respuesta = self.client.get(reverse("catalogo:detalle", args=[producto.pk]))
        self.assertContains(respuesta, 'data-bs-interval="5000"')
        self.assertContains(respuesta, 'data-bs-pause="hover"')
        self.assertContains(respuesta, 'class="miniatura-galeria activa"')
        self.assertContains(respuesta, 'class="miniatura-galeria"')
        self.assertContains(respuesta, "prefers-reduced-motion")
