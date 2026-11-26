"""Nov 2026: píldoras «En oferta» y «Oferta vencida» en Mis productos, y el botón para quitar las vencidas."""

from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from .tests import BaseCatalogo


class BaseOfertasMisProductos(BaseCatalogo):
    def setUp(self):
        super().setUp()
        hoy = timezone.localdate()
        self.crear_producto(nombre="Normal", precio=Decimal("100.00"))
        self.crear_producto(nombre="Oferta sin fecha", precio=Decimal("100.00"), precio_oferta=Decimal("80.00"))
        self.crear_producto(nombre="Oferta hasta mañana", precio=Decimal("100.00"), precio_oferta=Decimal("90.00"),
                            oferta_hasta=hoy + timedelta(days=1))
        self.crear_producto(nombre="Oferta vencida", precio=Decimal("100.00"), precio_oferta=Decimal("70.00"),
                            oferta_hasta=hoy - timedelta(days=1))
        self.crear_producto(tienda=self.otra_tienda, nombre="Oferta de otra tienda",
                            precio=Decimal("100.00"), precio_oferta=Decimal("50.00"))
        self.client.force_login(self.tienda.usuario)
        self.url = reverse("catalogo:mis_productos")

    def nombres(self, respuesta):
        return sorted(p.nombre for p in respuesta.context["pagina"])


class FiltroOfertasMisProductosTests(BaseOfertasMisProductos):
    def test_pildora_en_oferta_va_despues_de_todos_con_su_cantidad(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.context["resumen"]["en_oferta"], 2)
        html = respuesta.content.decode()
        self.assertIn('filtro-rapido--oferta', html)
        self.assertLess(html.index(">Todos <"), html.index(">En oferta <"))
        self.assertLess(html.index(">En oferta <"), html.index(">Stock bajo <"))

    def test_filtrar_solo_ofertas_vigentes_de_mi_tienda(self):
        respuesta = self.client.get(self.url, {"ver": "oferta"})
        self.assertEqual(self.nombres(respuesta), ["Oferta hasta mañana", "Oferta sin fecha"])

    def test_ofertas_vencidas(self):
        respuesta = self.client.get(self.url, {"ver": "oferta_vencida"})
        self.assertEqual(self.nombres(respuesta), ["Oferta vencida"])
        self.assertContains(respuesta, "La fecha límite de estas ofertas ya pasó")
        self.assertContains(respuesta, ">Oferta vencida</span>")

    def test_sin_vencidas_no_aparece_esa_pildora(self):
        from .models import Producto

        Producto.objects.filter(nombre="Oferta vencida").update(precio_oferta=None, oferta_hasta=None)
        self.assertNotContains(self.client.get(self.url), "ver=oferta_vencida")

    def test_numero_en_rojo_en_la_hoja_de_estilos(self):
        from django.contrib.staticfiles import finders

        with open(finders.find("css/marca.css"), encoding="utf-8") as archivo:
            self.assertIn(".filtro-rapido--oferta:not(.activo) .contador { background: #FDECEA; color: #C62828; }",
                          archivo.read())


class QuitarOfertasVencidasTests(BaseOfertasMisProductos):
    def test_boton_y_ventana_con_todas_las_vencidas_aunque_haya_categoria_elegida(self):
        from .models import Categoria

        otra, _ = Categoria.objects.get_or_create(nombre="Accesorios")
        respuesta = self.client.get(self.url, {"ver": "oferta_vencida", "categoria": otra.pk})
        self.assertContains(respuesta, 'data-bs-target="#modal-quitar-vencidas"')
        self.assertContains(respuesta, "Quitar la oferta vencida")
        self.assertEqual([p.nombre for p in respuesta.context["vencidas"]], ["Oferta vencida"])
        self.assertContains(respuesta, reverse("catalogo:quitar_ofertas_vencidas"))

    def test_quitar_deja_el_precio_normal_y_no_toca_las_vigentes_ni_otras_tiendas(self):
        from .models import Producto

        respuesta = self.client.post(reverse("catalogo:quitar_ofertas_vencidas"))
        self.assertRedirects(respuesta, self.url, fetch_redirect_response=False)
        vencida = Producto.objects.get(nombre="Oferta vencida")
        self.assertIsNone(vencida.precio_oferta)
        self.assertIsNone(vencida.oferta_hasta)
        self.assertEqual(vencida.precio, Decimal("100.00"))
        self.assertEqual(Producto.objects.get(nombre="Oferta sin fecha").precio_oferta, Decimal("80.00"))
        self.assertEqual(Producto.objects.get(nombre="Oferta hasta mañana").precio_oferta, Decimal("90.00"))
        self.assertEqual(self.client.get(self.url).context["resumen"]["oferta_vencida"], 0)

    def test_no_toca_las_vencidas_de_otra_tienda(self):
        from .models import Producto

        ajena = self.crear_producto(tienda=self.otra_tienda, nombre="Vencida ajena", precio=Decimal("100.00"),
                                    precio_oferta=Decimal("60.00"),
                                    oferta_hasta=timezone.localdate() - timedelta(days=3))
        self.client.post(reverse("catalogo:quitar_ofertas_vencidas"))
        self.assertEqual(Producto.objects.get(pk=ajena.pk).precio_oferta, Decimal("60.00"))

    def test_solo_por_post(self):
        self.assertEqual(self.client.get(reverse("catalogo:quitar_ofertas_vencidas")).status_code, 405)
