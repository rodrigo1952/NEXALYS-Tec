"""
Lo que hace distinta a cada tienda (nov 2026): frase corta, servicios que marca la tienda (más «otro servicio»)
y especialidades que salen solas de lo que vende. Se ven en el Inicio, en su perfil y en Tiendas cercanas (con filtro).
"""

from django.urls import reverse

from catalogo.models import Categoria
from catalogo.tests import BaseCatalogo

from .etiquetas import especialidades_por_tienda, etiquetas
from .inicio import productos_de_muestra, tiendas_para_inicio
from .models import Tienda
from .tests import crear_tienda


class EspecialidadesTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.laptops, _ = Categoria.objects.get_or_create(nombre="Laptops")
        self.otros, _ = Categoria.objects.get_or_create(nombre="Otros")

    def crear(self, cantidad, categoria, tienda=None, **datos):
        for n in range(cantidad):
            self.crear_producto(tienda=tienda, categoria=categoria, nombre=f"{categoria} {n}", **datos)

    def especialidades(self, tienda=None):
        tienda = tienda or self.tienda
        return [e["texto"] for e in especialidades_por_tienda([tienda.pk]).get(tienda.pk, [])]

    def test_las_categorias_con_peso_en_su_catalogo(self):
        self.crear(6, self.categoria)   # Celulares: 60 %
        self.crear(3, self.laptops)     # Laptops: 30 %
        self.crear(1, Categoria.objects.get_or_create(nombre="Audio")[0])  # 10 %: no
        self.assertEqual(self.especialidades(), ["Celulares", "Laptops"])

    def test_hacen_falta_al_menos_dos_productos(self):
        self.crear(1, self.categoria)
        self.assertEqual(self.especialidades(), [])

    def test_catalogo_muy_variado_no_tiene_especialidad(self):
        for nombre in ("Audio", "Tablets", "Pantallas", "Impresoras"):
            self.crear(2, Categoria.objects.get_or_create(nombre=nombre)[0])
        self.assertEqual(self.especialidades(), [])

    def test_otros_no_es_especialidad(self):
        self.crear(5, self.otros)
        self.assertEqual(self.especialidades(), [])

    def test_solo_cuentan_los_productos_publicados(self):
        self.crear(4, self.categoria, activo=False)
        self.crear(2, self.laptops)
        self.assertEqual(self.especialidades(), ["Laptops"])

    def test_cada_tienda_tiene_las_suyas(self):
        self.crear(3, self.categoria)
        self.crear(3, self.laptops, tienda=self.otra_tienda)
        datos = especialidades_por_tienda([self.tienda.pk, self.otra_tienda.pk])
        self.assertEqual([e["texto"] for e in datos[self.tienda.pk]], ["Celulares"])
        self.assertEqual([e["texto"] for e in datos[self.otra_tienda.pk]], ["Laptops"])


class EtiquetasTests(BaseCatalogo):
    def test_orden_lema_servicios_especialidades(self):
        self.tienda.lema = "Especialistas en laptops"
        self.tienda.impresoras_tintas = True
        self.tienda.repara_celulares = True
        self.tienda.otro_servicio = "Mantenimiento de consolas"
        lista = etiquetas(self.tienda, [{"id": 1, "texto": "Celulares"}])
        self.assertEqual([(e["tipo"], e["texto"]) for e in lista], [
            ("lema", "Especialistas en laptops"),
            ("servicio", "Reparación de celulares"),
            ("servicio", "Impresoras y tintas"),
            ("servicio", "Mantenimiento de consolas"),
            ("especialidad", "Celulares"),
        ])
        self.assertEqual(len(etiquetas(self.tienda, [], maximo=3)), 3)

    def test_sin_nada_no_hay_etiquetas(self):
        self.assertEqual(etiquetas(self.tienda, []), [])


class EditarLoQueTeHaceDistintoTests(BaseCatalogo):
    url = reverse("tiendas:editar")

    def setUp(self):
        super().setUp()
        self.client.force_login(self.tienda.usuario)

    def datos(self, **cambios):
        datos = {
            "datos-nombre": self.tienda.nombre, "datos-direccion": self.tienda.direccion,
            "datos-whatsapp": self.tienda.whatsapp, "datos-descripcion": "",
            "horario-TOTAL_FORMS": "0", "horario-INITIAL_FORMS": "0",
            "horario-MIN_NUM_FORMS": "0", "horario-MAX_NUM_FORMS": "7",
        }
        datos.update(cambios)
        return datos

    def test_la_seccion_aparece_en_editar(self):
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, "Lo que te hace distinto")
        self.assertContains(respuesta, "Servicios que das en tu local")
        for texto in ("Reparación de celulares", "Reparación de laptops y PC", "Cámaras y redes", "Impresoras y tintas"):
            self.assertContains(respuesta, texto)
        self.assertContains(respuesta, 'name="datos-otro_servicio"')

    def test_guardar_sin_pedir_la_contrasena(self):
        respuesta = self.client.post(self.url, self.datos(**{
            "datos-lema": "  Especialistas   en laptops ",
            "datos-repara_computadoras": "on",
            "datos-otro_servicio": "Ensamblaje de PC gamer",
        }))
        self.assertRedirects(respuesta, reverse("tiendas:panel"))
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.lema, "Especialistas en laptops")
        self.assertTrue(self.tienda.repara_computadoras)
        self.assertFalse(self.tienda.repara_celulares)
        self.assertEqual(self.tienda.otro_servicio, "Ensamblaje de PC gamer")

    def test_la_frase_tiene_limite(self):
        respuesta = self.client.post(self.url, self.datos(**{"datos-lema": "x" * 31}))
        self.assertEqual(respuesta.status_code, 200)
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.lema, "")

    def test_se_ven_en_el_panel(self):
        self.tienda.repara_celulares = True
        self.tienda.save()
        respuesta = self.client.get(reverse("tiendas:panel"))
        self.assertContains(respuesta, "Lo que te hace distinto")
        self.assertContains(respuesta, "etiqueta-tienda--servicio")


class EtiquetasEnElSitioTests(BaseCatalogo):
    def setUp(self):
        super().setUp()
        self.tienda.lema = "Especialistas en celulares"
        self.tienda.repara_celulares = True
        self.tienda.save()
        for n in range(3):
            self.crear_producto(nombre=f"Celular {n}")

    def test_perfil(self):
        respuesta = self.client.get(reverse("tiendas:perfil", args=[self.tienda.pk]))
        self.assertContains(respuesta, "etiquetas-tienda--grande")
        self.assertContains(respuesta, "Especialistas en celulares")
        self.assertContains(respuesta, "Reparación de celulares")
        self.assertContains(respuesta, '<li class="etiqueta-tienda etiqueta-tienda--especialidad">Celulares</li>', html=True)

    def test_tiendas_cercanas_con_filtros(self):
        respuesta = self.client.get(reverse("tiendas:cercanas"))
        self.assertContains(respuesta, "Todas (2)")
        self.assertContains(respuesta, 'href="?servicio=repara_celulares"')
        self.assertNotContains(respuesta, 'href="?servicio=impresoras_tintas"')  # ninguna tienda lo da
        self.assertContains(respuesta, f'href="?especialidad={self.categoria.pk}"')
        self.assertEqual(len(respuesta.context["tiendas"]), 2)

    def test_filtro_por_servicio(self):
        respuesta = self.client.get(reverse("tiendas:cercanas"), {"servicio": "repara_celulares"})
        self.assertEqual([t["nombre"] for t in respuesta.context["tiendas"]], ["Tienda Uno"])
        self.assertContains(respuesta, 'class="filtro-tienda activo"')

    def test_filtro_por_especialidad(self):
        respuesta = self.client.get(reverse("tiendas:cercanas"), {"especialidad": self.categoria.pk})
        self.assertEqual([t["nombre"] for t in respuesta.context["tiendas"]], ["Tienda Uno"])

    def test_un_filtro_inventado_se_ignora(self):
        for parametros in ({"servicio": "clave_actual"}, {"especialidad": "abc"}, {"especialidad": "999"}):
            respuesta = self.client.get(reverse("tiendas:cercanas"), parametros)
            self.assertEqual(len(respuesta.context["tiendas"]), 2)


class TarjetaDelInicioTests(BaseCatalogo):
    def test_toda_la_tarjeta_lleva_al_perfil_sin_botones(self):
        self.tienda.repara_celulares = True
        self.tienda.save()
        respuesta = self.client.get(reverse("inicio"))
        html = respuesta.content.decode()
        bloque = html[html.index('class="tiendas-inicio__lista"'):html.index("tiendas-inicio__todas")]
        self.assertIn(f'href="{reverse("tiendas:perfil", args=[self.tienda.pk])}" class="tienda-inicio__nombre stretched-link"', bloque)
        self.assertNotIn("wa.me", bloque)
        self.assertNotIn("Ver tienda", bloque)
        self.assertIn("Reparación de celulares", bloque)

    def test_productos_de_muestra_con_stock_y_destacados_primero(self):
        viejo = self.crear_producto(nombre="Viejo")
        self.crear_producto(nombre="Agotado", stock=0)
        self.crear_producto(nombre="Oculto", activo=False)
        destacado = self.crear_producto(nombre="Destacado", destacado=True)
        nuevo = self.crear_producto(nombre="Nuevo")
        otro = self.crear_producto(nombre="Otro")
        self.assertEqual(productos_de_muestra(self.tienda), [destacado, otro, nuevo])
        self.assertNotIn(viejo, productos_de_muestra(self.tienda))

    def test_hasta_tres_etiquetas(self):
        tienda = crear_tienda("tienda3", "Tienda Tres", "933333333")
        Tienda.objects.filter(pk=tienda.pk).update(
            lema="Todo en tecnología", repara_celulares=True, repara_computadoras=True, impresoras_tintas=True)
        tiendas, _ = tiendas_para_inicio()
        tres = next(t for t in tiendas if t["tienda"].pk == tienda.pk)
        self.assertEqual([e["texto"] for e in tres["etiquetas"]],
                         ["Todo en tecnología", "Reparación de celulares", "Reparación de laptops y PC"])
