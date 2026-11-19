"""
Nov 2026: la contraseña para guardar datos sensibles (cuentas/reautenticacion.py) ya no queda escondida.

- Va justo encima de «Guardar cambios» (templates/_confirmar_clave.html) y dice qué cambió.
- static/js/formularios.js la muestra apenas cambias un dato sensible y, si el formulario vuelve
  con errores, la página baja hasta el primero y lo resalta (en todos los formularios).
- En el mapa de «Editar mi tienda», si el pin quedó distinto de lo guardado, se avisa y se puede deshacer.
"""

import re
from decimal import Decimal

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from tiendas.test_ubicacion import BaseUbicacion

from .test_perfil import CLAVE, crear_cliente


def estatico(ruta):
    with open(finders.find(ruta), encoding="utf-8") as archivo:
        return archivo.read()


def etiqueta(html, nombre):
    """La etiqueta <input> completa del campo con ese name."""
    return re.search(r'<input[^>]*name="%s"[^>]*>' % re.escape(nombre), html).group(0)


class ContrasenaEnEditarTiendaTests(BaseUbicacion):
    def setUp(self):
        self.tienda = self.crear_tienda("Kantu Tech", "944444444",
                                        latitud=Decimal("-12.869000"), longitud=Decimal("-72.691500"))
        self.client.force_login(self.tienda.usuario)
        self.url = reverse("tiendas:editar")

    def datos(self, **cambios):
        datos = {
            "datos-nombre": "Kantu Tech", "datos-direccion": "Jr. Espinar, Quillabamba", "datos-whatsapp": "944444444",
            "datos-descripcion": "", "datos-latitud": "-12.869000", "datos-longitud": "-72.691500",
        }
        datos.update(cambios)
        return datos

    def test_la_contrasena_va_justo_encima_del_boton(self):
        html = self.client.get(self.url).content.decode()
        caja = html.index("data-confirmar-clave")
        self.assertGreater(caja, html.index('id="titulo-horario"'))  # ya no está a media página
        self.assertLess(caja, html.index("Guardar cambios</button>"))
        self.assertEqual(html.count('name="datos-clave_actual"'), 1)
        self.assertIn("Falta un paso: confirma que eres tú", html)
        self.assertNotIn("data-formulario-enviado", html)  # al entrar no se baja a ningún lado

    def test_cada_dato_sensible_lleva_su_valor_guardado(self):
        html = self.client.get(self.url).content.decode()
        whatsapp = etiqueta(html, "datos-whatsapp")
        for texto in ('data-sensible="WhatsApp"', 'data-sensible-tipo="telefono"', 'data-sensible-original="944444444"'):
            self.assertIn(texto, whatsapp)
        latitud = etiqueta(html, "datos-latitud")
        for texto in ('data-sensible="ubicación en el mapa"', 'data-sensible-tipo="numero"',
                      'data-sensible-original="-12.869000"'):
            self.assertIn(texto, latitud)
        self.assertIn('data-sensible-tipo="texto"', etiqueta(html, "datos-nombre"))
        self.assertNotIn("data-sensible", etiqueta(html, "datos-lema"))  # lo que no pide contraseña, no se marca

    def test_dice_que_cambio_cuando_falta_la_contrasena(self):
        respuesta = self.client.post(self.url, self.datos(**{"datos-latitud": "-12.870000"}))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Cambiaste: <strong>ubicación en el mapa</strong>.")
        self.assertContains(respuesta, "confirmar-clave--error")
        self.assertContains(respuesta, "Para guardar estos cambios, escribe tu contraseña actual.")
        self.assertContains(respuesta, "data-formulario-enviado")  # la página baja hasta la contraseña

        respuesta = self.client.post(self.url, self.datos(**{
            "datos-direccion": "Jr. Libertad, Quillabamba", "datos-whatsapp": "955555555", "datos-clave_actual": "otra"}))
        self.assertContains(respuesta, "Cambiaste: <strong>dirección y WhatsApp</strong>.")
        self.assertContains(respuesta, "La contraseña no es correcta.")
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.whatsapp, "944444444")

    def test_sin_datos_sensibles_no_pide_contrasena(self):
        respuesta = self.client.post(self.url, self.datos(**{"datos-lema": "Especialistas en laptops",
                                                               "datos-whatsapp": "944 444 444"}))
        self.assertRedirects(respuesta, reverse("tiendas:panel"))
        self.tienda.refresh_from_db()
        self.assertEqual(self.tienda.lema, "Especialistas en laptops")

    def test_el_mapa_sabe_cual_es_la_ubicacion_guardada(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('data-guardada-lat="-12.869000" data-guardada-lng="-72.691500"', html)
        # Si vuelve con errores, el pin muestra lo nuevo, pero «Deshacer» regresa a lo guardado.
        respuesta = self.client.post(self.url, self.datos(**{"datos-latitud": "-12.870000"}))
        self.assertContains(respuesta, 'data-guardada-lat="-12.869000"')
        self.assertIn('value="-12.870000"', etiqueta(respuesta.content.decode(), "datos-latitud"))

    def test_sin_ubicacion_guardada(self):
        self.tienda.latitud = self.tienda.longitud = None
        self.tienda.save()
        html = self.client.get(self.url).content.decode()
        self.assertIn('data-guardada-lat="" data-guardada-lng=""', html)
        self.assertIn('data-sensible-original=""', etiqueta(html, "datos-latitud"))

    def test_despues_de_confirmar_no_se_vuelve_a_pedir(self):
        respuesta = self.client.post(self.url, self.datos(**{"datos-whatsapp": "955555555", "datos-clave_actual": "Clave#2026"}))
        self.assertRedirects(respuesta, reverse("tiendas:panel"))
        html = self.client.get(self.url).content.decode()
        self.assertNotIn("data-confirmar-clave", html)
        self.assertNotIn("data-sensible", html)


class ContrasenaEnEditarMisDatosTests(TestCase):
    def setUp(self):
        self.client.force_login(crear_cliente())
        self.url = reverse("editar_datos")

    def test_va_encima_del_boton_y_dice_que_cambio(self):
        html = self.client.get(self.url).content.decode()
        self.assertLess(html.index('name="email"'), html.index("data-confirmar-clave"))
        self.assertLess(html.index("data-confirmar-clave"), html.index("Guardar cambios</button>"))
        self.assertIn('data-sensible-tipo="correo"', etiqueta(html, "email"))
        respuesta = self.client.post(self.url, {"first_name": "Ana María", "last_name": "Quispe",
                                                "email": "cliente1@ejemplo.com", "clave_actual": ""})
        self.assertContains(respuesta, "Cambiaste: <strong>nombres</strong>.")
        respuesta = self.client.post(self.url, {"first_name": "Ana María", "last_name": "Quispe",
                                                "email": "cliente1@ejemplo.com", "clave_actual": CLAVE})
        self.assertRedirects(respuesta, reverse("mi_cuenta"))


class ScriptsTests(TestCase):
    def test_formularios_js_en_todas_las_paginas(self):
        self.assertContains(self.client.get(reverse("inicio")), "js/formularios.js")
        codigo = estatico("js/formularios.js")
        for texto in ('querySelectorAll("[data-confirmar-clave]")', "data-formulario-enviado", "scrollIntoView",
                      "Escribe tu contraseña actual para guardar estos cambios.", "}, true);"):
            self.assertIn(texto, codigo)

    def test_deshacer_el_pin(self):
        codigo = estatico("js/mapas.js")
        for texto in ("data-deshacer-pin", "Moviste el pin.", "Quitaste tu local del mapa.",
                      'latitud.dispatchEvent(new Event("change", { bubbles: true }))', "elemento.dataset.guardadaLat"):
            self.assertIn(texto, codigo)

    def test_estilos(self):
        css = estatico("css/marca.css")
        for texto in (".confirmar-clave[hidden]{ display: none; }", ".campo-resaltado{", ".aviso-pin__deshacer{"):
            self.assertIn(texto, css)
