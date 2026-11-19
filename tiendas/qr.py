"""
Código QR de la tienda: lleva a su página en NEXALYS Tec (enlace completo con SITIO_URL).
Lo genera la librería segno (pura Python, licencia BSD). Nivel de corrección «Q»: se sigue leyendo
aunque el cartel esté un poco sucio o arrugado.

El QR lleva la marca «?desde=qr»: así la página de la tienda (views.perfil) cuenta los escaneos
(modelo EscaneoQR) y la tienda los ve en «Mi código QR». El enlace que se comparte por WhatsApp
o redes va sin la marca: solo cuentan los escaneos del código.
"""

import io
from datetime import datetime, time, timedelta

import segno
from django.utils import timezone

AZUL_MARINO = "#0B1B3A"
MARCA = "qr"                     # lo que va en ?desde=
CLAVE_SESION = "qr_tiendas"      # tiendas cuyo QR ya se contó en esta visita
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre")


def enlace(tienda):
    """Lo que lleva el código: la página de la tienda con la marca para contar el escaneo."""
    return f"{tienda.enlace_publico()}?desde={MARCA}"


def crear(tienda):
    return segno.make(enlace(tienda), error="q")


def svg(tienda):
    """SVG para mostrar dentro de la página (se agranda sin perder nitidez)."""
    return crear(tienda).svg_inline(scale=10, border=2, dark=AZUL_MARINO, omitsize=True)


def archivo(tienda, formato):
    """Bytes del QR para descargar: «png» (para WhatsApp o Word) o «svg» (para imprenta)."""
    salida = io.BytesIO()
    if formato == "png":
        crear(tienda).save(salida, kind="png", scale=16, border=4, dark=AZUL_MARINO)
    else:
        crear(tienda).save(salida, kind="svg", scale=16, border=4, dark=AZUL_MARINO, xmldecl=True)
    return salida.getvalue()


def registrar_escaneo(request, tienda):
    """
    Cuenta un escaneo del QR de la tienda: una vez por visita (se anota en la sesión) y sin contar
    a la propia tienda ni al administrador probando el código. Devuelve True si lo contó.
    """
    from cuentas.views import tiene_rol

    from .models import EscaneoQR

    contadas = request.session.get(CLAVE_SESION, [])
    usuario = request.user
    if tienda.pk in contadas or getattr(usuario, "tienda", None) == tienda or tiene_rol(usuario, "Administrador"):
        return False
    EscaneoQR.objects.create(tienda=tienda)
    request.session[CLAVE_SESION] = contadas + [tienda.pk]
    return True


def _inicio_del_dia(dia):
    return timezone.make_aware(datetime.combine(dia, time.min))


def resumen_escaneos(tienda):
    """Números para «Mi código QR»: este mes, el mes pasado, el total y el último escaneo."""
    from .models import hora_12

    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    inicio_anterior = (inicio_mes - timedelta(days=1)).replace(day=1)
    escaneos = tienda.escaneos_qr.all()
    este_mes = escaneos.filter(fecha__gte=_inicio_del_dia(inicio_mes)).count()
    mes_anterior = escaneos.filter(fecha__gte=_inicio_del_dia(inicio_anterior), fecha__lt=_inicio_del_dia(inicio_mes)).count()

    ultimo = escaneos.order_by("-fecha").values_list("fecha", flat=True).first()
    texto_ultimo = ""
    if ultimo:
        ultimo = timezone.localtime(ultimo)
        dias = (hoy - ultimo.date()).days
        dia = "Hoy" if dias == 0 else "Ayer" if dias == 1 else f"{ultimo.day} de {MESES[ultimo.month - 1]}"
        texto_ultimo = f"{dia}, {hora_12(ultimo.time())}"

    nombre_anterior = MESES[inicio_anterior.month - 1]
    diferencia = este_mes - mes_anterior
    if diferencia > 0:
        comparacion = f"{diferencia} más que en {nombre_anterior}"
    elif diferencia < 0:
        comparacion = f"{-diferencia} menos que en {nombre_anterior}"
    else:
        comparacion = f"igual que en {nombre_anterior}" if este_mes else ""
    return {
        "este_mes": este_mes,
        "mes_anterior": mes_anterior,
        "diferencia": diferencia,
        "comparacion": comparacion,
        "total": escaneos.count(),
        "ultimo": texto_ultimo,
    }
