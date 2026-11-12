"""
«Descargar mis datos» (derecho de acceso, Ley 29733): todo lo que la página guarda de la persona,
en un archivo JSON que se puede abrir con el Bloc de notas o con cualquier programa.
Nunca incluye la contraseña (ni cifrada).
"""

import json

from django.conf import settings
from django.utils import timezone

from .models import ConsentimientoPrivacidad, SolicitudDerecho


def _fecha(valor):
    return timezone.localtime(valor).strftime("%d/%m/%Y %H:%M") if valor else None


def datos_de(usuario):
    datos = {
        "generado_el": _fecha(timezone.now()),
        "sitio": settings.SITIO_URL,
        "cuenta": {
            "usuario": usuario.username,
            "nombres": usuario.first_name,
            "apellidos": usuario.last_name,
            "correo": usuario.email,
            "rol": [grupo.name for grupo in usuario.groups.all()],
            "registrada_el": _fecha(usuario.date_joined),
            "ultimo_ingreso": _fecha(usuario.last_login),
        },
        "politica_de_privacidad_aceptada": [
            {"version": c.version, "fecha": _fecha(c.fecha), "donde": c.get_origen_display()}
            for c in ConsentimientoPrivacidad.objects.filter(usuario=usuario)
        ],
        "favoritos": [
            {
                "producto": f.producto.nombre,
                "tienda": f.producto.tienda.nombre,
                "precio_al_guardarlo": str(f.precio_guardado),
                "guardado_el": _fecha(f.creado),
            }
            for f in usuario.favoritos.select_related("producto__tienda")
        ],
        "solicitudes_de_derechos": [
            {
                "tipo": s.nombre_corto_tipo,
                "recibida_el": _fecha(s.creada),
                "estado": s.get_estado_display(),
                "detalle": s.detalle,
                "respuesta": s.respuesta,
            }
            for s in SolicitudDerecho.objects.filter(usuario=usuario)
        ],
    }
    tienda = getattr(usuario, "tienda", None)
    if tienda is not None:
        datos["tienda"] = {
            "nombre": tienda.nombre,
            "direccion": tienda.direccion,
            "whatsapp": tienda.whatsapp,
            "descripcion": tienda.descripcion,
            "ubicacion_en_el_mapa": (
                {"latitud": str(tienda.latitud), "longitud": str(tienda.longitud)} if tienda.tiene_ubicacion else None
            ),
            "logo": settings.SITIO_URL + tienda.logo.url if tienda.logo else None,
            "estado": tienda.get_estado_display(),
            "registrada_el": _fecha(tienda.creada_en),
            "horario": [str(dia) for dia in tienda.horarios.all()],
            "productos": [
                {"nombre": p.nombre, "precio": str(p.precio), "stock": p.stock, "publicado": p.activo}
                for p in tienda.productos.order_by("nombre")
            ],
            "nota": "Las ventas y el inventario de tu tienda se descargan en Excel desde el reporte de Inventario.",
        }
    return datos


def archivo_json(usuario):
    return json.dumps(datos_de(usuario), ensure_ascii=False, indent=2)
