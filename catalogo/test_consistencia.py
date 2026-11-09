"""
Consistencia visual del sitio: menú con el mismo orden para todos, íconos de línea en vez de emojis,
botón de favoritos, sistema de botones, cifras alineadas, mensajes con ícono, impresión de la nota,
ventana para anular una venta, tarjetas grises de carga y pie de página completo.
"""

import re

from django.contrib.auth.models import Group, User
from django.contrib.staticfiles import finders
from django.urls import reverse

from inventario.servicios import LineaPedida, registrar_venta

from .tests import BaseCatalogo

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐]")


def leer_estatico(ruta):
    with open(finders.find(ruta), encoding="utf-8") as archivo:
        return archivo.read()


class ConsistenciaTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.producto = self.crear_producto(nombre="Galaxy A15", destacado=True, stock=4)
        self.cliente = User.objects.create_user("cliente1", password="Clave#2026")
        self.cliente.groups.add(Group.objects.get_or_create(name="Cliente")[0])

    def test_menu_del_cliente_mismo_orden_y_favoritos_al_final(self):
        self.client.force_login(self.cliente)
        html = self.client.get(reverse("inicio")).content.decode()
        menu = html[html.index('class="navbar-nav menu-secciones'):]
        orden = [menu.index(f'href="{reverse(n)}"') for n in ("inicio", "catalogo:catalogo", "tiendas:cercanas", "favoritos:lista")]
        self.assertEqual(orden, sorted(orden))
        self.assertLess(menu.index("menu-secciones__separador"), orden[-1])

    def test_sin_emojis_en_las_paginas(self):
        self.client.force_login(self.cliente)
        for url in (reverse("inicio"), reverse("catalogo:catalogo"), reverse("catalogo:detalle", args=[self.producto.pk]),
                    reverse("favoritos:lista"), reverse("tiendas:cercanas")):
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                visible = re.sub(r"<!--.*?-->|\{#.*?#\}", "", html, flags=re.S)
                self.assertIsNone(EMOJI.search(visible), EMOJI.search(visible) and visible[EMOJI.search(visible).start() - 80:][:120])

    def test_corazon_blanco_y_marcado_azul(self):
        self.client.force_login(self.cliente)
        respuesta = self.client.get(reverse("catalogo:catalogo"))
        self.assertContains(respuesta, 'class="boton-corazon" title="Guardar en favoritos"')
        self.assertContains(respuesta, '<i class="bi bi-heart" data-icono aria-hidden="true"></i>')
        css = leer_estatico("css/marca.css")
        self.assertIn(".boton-corazon--marcado, .boton-corazon--marcado:hover { background: var(--nx-oscuro);", css)

    def test_iconos_de_linea_en_el_inicio(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertContains(respuesta, '<i class="bi bi-star" aria-hidden="true"></i> Productos destacados')
        self.assertContains(respuesta, '<i class="bi bi-shop" aria-hidden="true"></i> <a')

    def test_tabla_de_mis_productos_dice_favoritos(self):
        self.client.force_login(self.tienda.usuario)
        respuesta = self.client.get(reverse("catalogo:mis_productos"))
        self.assertContains(respuesta, '<i class="bi bi-heart" aria-hidden="true"></i> Favoritos</th>')

    def test_barra_fija_para_guardar_el_producto(self):
        self.client.force_login(self.tienda.usuario)
        respuesta = self.client.get(reverse("catalogo:crear"))
        self.assertContains(respuesta, 'class="barra-guardar"')
        self.assertContains(respuesta, '<button type="submit" class="btn btn-primary">Guardar producto</button>')
        self.assertIn(".barra-guardar {\n  position: sticky; bottom: 0;", leer_estatico("css/marca.css"))

    def test_sistema_de_botones_cifras_ayudas_y_mensajes(self):
        css = leer_estatico("css/marca.css")
        self.assertIn("min-height: 46px; display: inline-flex;", css)
        self.assertIn("--bs-btn-border-radius: 12px;", css)
        self.assertIn(".btn-sm { --bs-btn-border-radius: 10px; --bs-btn-padding-x: .7rem; min-height: 32px;", css)
        self.assertIn(".table, .nota-venta, .precio { font-variant-numeric: tabular-nums; }", css)
        self.assertIn("--nx-texto-suave: #46566D;", css)
        for regla in ('.alert-success::before { content: "\\f633"; }', '.alert-warning::before { content: "\\f333"; }',
                      '.alert-danger::before { content: "\\f659"; }'):
            self.assertIn(regla, css)

    def test_pie_de_pagina_completo(self):
        respuesta = self.client.get(reverse("inicio"))
        for parte in ('pie-marca__columnas"', f'href="{reverse("tiendas:cercanas")}">Tiendas cercanas</a>',
                      f'href="{reverse("ayuda")}">Ayuda y soporte</a>', f'href="{reverse("privacidad")}">Privacidad y términos</a>',
                      "Proyecto IV ciclo · IESTP Urusayhua · 2026"):
            self.assertContains(respuesta, parte)

    def test_tarjetas_grises_de_carga(self):
        codigo = leer_estatico("js/catalogo.js")
        self.assertIn('form.addEventListener("submit", mostrarCarga);', codigo)
        self.assertIn('class="tarjeta-esqueleto"', codigo)
        self.assertContains(self.client.get(reverse("inicio")), 'img.classList.add("foto-cargando");')


class NotaDeVentaTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.producto = self.crear_producto(nombre="Galaxy A15", stock=4)
        self.client.force_login(self.tienda.usuario)
        self.venta = registrar_venta(self.tienda, self.tienda.usuario, [LineaPedida(self.producto.pk, 1)])

    def test_ventana_para_anular_con_motivo(self):
        respuesta = self.client.get(reverse("inventario:venta_detalle", args=[self.venta.pk]))
        self.assertContains(respuesta, 'data-bs-target="#modal-anular-venta">Anular venta</a>')
        self.assertContains(respuesta, f'action="{reverse("inventario:venta_anular", args=[self.venta.pk])}"')
        self.assertContains(respuesta, "Se devolverán al stock estos productos:")
        self.assertContains(respuesta, "1 × Galaxy A15")
        self.assertContains(respuesta, 'name="motivo"')
        self.assertContains(respuesta, "Esta acción no se puede deshacer.")
        self.assertContains(respuesta, ">Sí, anular venta</button>")

    def test_anular_desde_la_ventana(self):
        url = reverse("inventario:venta_anular", args=[self.venta.pk])
        self.assertRedirects(self.client.post(url, {"motivo": "Se registró dos veces"}),
                             reverse("inventario:venta_detalle", args=[self.venta.pk]))
        self.venta.refresh_from_db()
        self.assertTrue(self.venta.anulada)
        self.assertNotContains(self.client.get(reverse("inventario:venta_detalle", args=[self.venta.pk])), "modal-anular-venta")

    def test_al_imprimir_solo_la_nota(self):
        css = leer_estatico("css/marca.css")
        bloque = css[css.index("@media print {"):]
        bloque = bloque[:bloque.index("\n}\n")]
        for parte in (".cabecera-marca, .pie-marca, .no-imprimir", ".nota-venta__columna { flex: 0 0 100%; max-width: 100%; }",
                      ".barra-categorias, .modal, .modal-backdrop"):
            self.assertIn(parte, bloque)
        self.assertContains(self.client.get(reverse("inventario:venta_detalle", args=[self.venta.pk])), 'class="col-lg-8 nota-venta__columna"')
