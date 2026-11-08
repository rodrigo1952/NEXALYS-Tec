"""
Galería única al agregar y editar un producto: todas las fotos en una lista, la primera es la
principal. El navegador envía el orden final en «galeria_plan» (p, f12, n0) y las fotos nuevas
en «fotos_nuevas». También: Publicado y Destacado como tarjetas con interruptor.
"""

import shutil
import tempfile

from django.test import override_settings
from django.urls import reverse
from PIL import Image

from .models import FotoProducto, Producto
from .test_fotos import foto
from .tests import BaseCatalogo

CARPETA_MEDIA = tempfile.mkdtemp()
COLORES = {"red": (255, 0, 0), "green": (0, 128, 0), "blue": (0, 0, 255), "yellow": (255, 255, 0), "purple": (128, 0, 128)}


def color(campo):
    """Nombre del color de la imagen guardada (las fotos de prueba son de un solo color)."""
    with campo.storage.open(campo.name, "rb") as archivo:
        pixel = Image.open(archivo).convert("RGB").getpixel((5, 5))
    return min(COLORES, key=lambda nombre: sum((a - b) ** 2 for a, b in zip(COLORES[nombre], pixel)))


@override_settings(MEDIA_ROOT=CARPETA_MEDIA)
class PlanDeFotosTests(BaseCatalogo):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CARPETA_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.client.force_login(self.tienda.usuario)

    def colores(self, producto):
        producto.refresh_from_db()
        principal = [color(producto.imagen)] if producto.imagen else []
        return principal + [color(f.imagen) for f in producto.fotos.all()]

    def crear_con_fotos(self, *nombres, nombre="Galaxy A15"):
        producto = self.crear_producto(nombre=nombre, imagen=foto("principal.png", color=nombres[0]))
        for orden, nombre in enumerate(nombres[1:], start=1):
            FotoProducto.objects.create(producto=producto, imagen=foto(f"{nombre}.png", color=nombre), orden=orden)
        return producto

    def editar(self, producto, plan, nuevas=()):
        url = reverse("catalogo:editar", args=[producto.pk])
        version = self.client.get(url).context["form"]["version"].value()
        datos = self.datos_formulario(nombre="Galaxy A15", version=version, galeria_plan=plan)
        if nuevas:
            datos["fotos_nuevas"] = [foto(f"{c}.png", color=c) for c in nuevas]
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(url, datos)

    def test_al_crear_la_primera_es_la_principal_y_las_demas_adicionales(self):
        datos = self.datos_formulario(galeria_plan="n0,n1,n2",
                                      fotos_nuevas=[foto(f"{c}.png", color=c) for c in ("blue", "red", "green")])
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(reverse("catalogo:crear"), datos)
        producto = Producto.objects.get(nombre="Galaxy A25")
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.colores(producto), ["blue", "red", "green"])

    def test_al_crear_se_respeta_el_orden_elegido_antes_de_guardar(self):
        # El navegador entrega las fotos en un orden; la tienda arrastró la última a la principal.
        datos = self.datos_formulario(galeria_plan="n2,n0,n1",
                                      fotos_nuevas=[foto(f"{c}.png", color=c) for c in ("blue", "red", "green")])
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("catalogo:crear"), datos)
        self.assertEqual(self.colores(Producto.objects.get(nombre="Galaxy A25")), ["green", "blue", "red"])

    def test_una_foto_nueva_pasa_a_principal_y_la_anterior_queda_adicional(self):
        producto = self.crear_con_fotos("red", "green")
        verde = producto.fotos.get()
        respuesta = self.editar(producto, f"n0,p,f{verde.pk}", nuevas=["blue"])
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.colores(producto), ["blue", "red", "green"])

    def test_intercambiar_adicionales_y_principal(self):
        producto = self.crear_con_fotos("red", "green", "blue")
        verde, azul = producto.fotos.all()
        self.editar(producto, f"f{azul.pk},f{verde.pk},p")
        self.assertEqual(self.colores(producto), ["blue", "green", "red"])

    def test_quitar_la_principal_sube_la_siguiente_y_borra_el_archivo(self):
        producto = self.crear_con_fotos("red", "green")
        verde = producto.fotos.get()
        archivo_rojo = producto.imagen.name
        self.editar(producto, f"f{verde.pk}")
        self.assertEqual(self.colores(producto), ["green"])
        self.assertFalse(producto.imagen.storage.exists(archivo_rojo))
        self.assertEqual(producto.fotos.count(), 0)

    def test_reemplazar_una_adicional_en_su_lugar(self):
        producto = self.crear_con_fotos("red", "green", "blue")
        verde, azul = producto.fotos.all()
        archivo_verde = verde.imagen.name
        self.editar(producto, f"p,n0,f{azul.pk}", nuevas=["yellow"])
        self.assertEqual(self.colores(producto), ["red", "yellow", "blue"])
        self.assertFalse(producto.imagen.storage.exists(archivo_verde))

    def test_sin_fotos(self):
        producto = self.crear_con_fotos("red", "green")
        self.editar(producto, "ninguna")
        self.assertEqual(self.colores(producto), [])

    def test_ficha_ajena_o_inexistente_no_cambia_nada(self):
        producto = self.crear_con_fotos("red", "green")
        otro = self.crear_con_fotos("blue", "yellow", nombre="Otro producto")
        ajena = otro.fotos.get()
        respuesta = self.editar(producto, f"f{ajena.pk},p")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Las fotos cambiaron mientras editabas")
        self.assertEqual(self.colores(producto), ["red", "green"])

    def test_maximo_seis_fotos_en_total(self):
        producto = self.crear_con_fotos("red")
        respuesta = self.editar(producto, "p,n0,n1,n2,n3,n4,n5", nuevas=["green"] * 6)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Puedes tener hasta 6 fotos en total")
        self.assertEqual(self.colores(producto), ["red"])

    def test_sin_plan_se_usan_los_campos_de_antes(self):
        # Formularios antiguos (o sin JavaScript): «fotos_nuevas» se agregan como adicionales.
        producto = self.crear_con_fotos("red")
        self.editar(producto, "", nuevas=["green"])
        self.assertEqual(self.colores(producto), ["red", "green"])


class InterruptoresTests(BaseCatalogo):
    def test_publicado_y_destacado_son_tarjetas_con_interruptor(self):
        self.client.force_login(self.tienda.usuario)
        respuesta = self.client.get(reverse("catalogo:crear"))
        self.assertContains(respuesta, 'class="interruptor interruptor--verde" for="id_activo"')
        self.assertContains(respuesta, 'class="interruptor interruptor--ambar" for="id_destacado"')
        self.assertContains(respuesta, 'role="switch"', count=2)
        # Van uno al lado del otro (misma fila), con una ayuda corta.
        html = respuesta.content.decode()
        fila = html[html.index('<div class="row g-3 mb-3">', html.index('id="id_stock_minimo"')):]
        self.assertLess(fila.index('for="id_activo"'), fila.index('for="id_destacado"'))
        self.assertLess(fila.index('for="id_destacado"'), fila.index('</div>\n    </div>') if '</div>\n    </div>' in fila else len(fila))
        self.assertContains(respuesta, "Desmárcalo para ocultarlo sin eliminarlo.")
        self.assertContains(respuesta, "Máximo 3 por tienda.")
        for texto in ("Sí: se ve en el catálogo", "No: está oculto, los clientes no lo ven",
                      "Sí: aparece entre los destacados del inicio", "No: no aparece entre los destacados"):
            self.assertContains(respuesta, texto)


class ArrastreDeFotosTests(BaseCatalogo):
    def test_una_foto_arrastrada_se_intercambia_y_no_se_copia(self):
        # Chrome/Brave también ponen la imagen arrastrada como «archivo»: la galería debe
        # reconocer primero que es una de sus fotos (se intercambian) y no tratarla como una
        # imagen nueva de la carpeta (que reemplazaría a la otra y la duplicaría).
        from .test_galeria import galeria_js

        codigo = galeria_js()
        self.assertIn("return arrastrada !== null || ", codigo)
        self.assertIn('return !traeFoto(evento) && Array.prototype.indexOf.call(evento.dataTransfer.types, "Files") !== -1;', codigo)
        self.assertLess(codigo.index("if (traeFoto(evento)) {"), codigo.index("if (traeArchivos(evento)) {"))
