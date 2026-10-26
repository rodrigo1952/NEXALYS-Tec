"""
Datos de demostración (Etapa 4): las mismas tiendas, productos e imágenes en cualquier PC.

GitHub guarda el código, pero NO la base de datos (db.sqlite3) ni las imágenes
(media/), a propósito. Para tener los mismos datos de prueba en tu PC y en el
laboratorio:

    En la PC que tiene los datos:   python manage.py exportar_demo
                                    git add demo  &&  git commit  &&  git push
    En la otra PC:                  git pull
                                    python manage.py migrate
                                    python manage.py cargar_demo

Qué se exporta: tiendas (con su horario y logo), productos (con sus fotos), y las
categorías y marcas que usan. NO se exportan clientes, ventas, inventario, favoritos ni
contraseñas. Los correos se reemplazan por correos de demostración, para no
publicar correos reales en GitHub.

Al cargar, cada cuenta de tienda queda con la contraseña CLAVE_DEMO.
"""

import json
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files import File
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from tiendas.models import HorarioDia, Tienda

from .models import Categoria, FotoProducto, Marca, Producto

CLAVE_DEMO = "Demo#2026"
VERSION = 1


def carpeta_por_defecto():
    return Path(settings.BASE_DIR) / "demo"


def correo_demo(usuario):
    return f"{slugify(usuario) or 'tienda'}@demo.nexalys.pe"


# ---------------------------------------------------------------------------
# Exportar
# ---------------------------------------------------------------------------

def exportar(carpeta=None):
    """Escribe demo/datos.json y copia las imágenes a demo/imagenes/. Devuelve un resumen."""
    carpeta = Path(carpeta or carpeta_por_defecto())
    imagenes = carpeta / "imagenes"
    if imagenes.exists():
        shutil.rmtree(imagenes)  # se reemplaza la exportación anterior completa
    imagenes.mkdir(parents=True)
    faltantes = []

    def copiar(campo):
        """Copia la imagen (si existe) y devuelve su ruta dentro de demo/imagenes/."""
        if not campo:
            return ""
        origen = Path(settings.MEDIA_ROOT) / campo.name
        if not origen.exists():
            faltantes.append(campo.name)
            return ""
        destino = imagenes / campo.name
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origen, destino)
        return campo.name.replace("\\", "/")

    tiendas = []
    for tienda in Tienda.objects.select_related("usuario").prefetch_related("horarios"):
        tiendas.append({
            "usuario": tienda.usuario.username,
            "nombres": tienda.usuario.first_name,
            "apellidos": tienda.usuario.last_name,
            "nombre": tienda.nombre,
            "direccion": tienda.direccion,
            "whatsapp": tienda.whatsapp,
            "descripcion": tienda.descripcion,
            "estado": tienda.estado,
            "motivo_suspension": tienda.motivo_suspension,
            "verificada": tienda.verificada_en is not None,
            "logo": copiar(tienda.logo),
            "horarios": [
                {
                    "dia": h.dia,
                    "abre": h.abre.isoformat() if h.abre else None,
                    "cierra": h.cierra.isoformat() if h.cierra else None,
                    "descanso_inicio": h.descanso_inicio.isoformat() if h.descanso_inicio else None,
                    "descanso_fin": h.descanso_fin.isoformat() if h.descanso_fin else None,
                }
                for h in tienda.horarios.all()
            ],
        })

    productos = []
    for producto in Producto.objects.select_related("tienda", "categoria", "marca").prefetch_related("fotos"):
        productos.append({
            "tienda": producto.tienda.nombre,
            "nombre": producto.nombre,
            "categoria": producto.categoria.nombre,
            "marca": producto.marca.nombre,
            "descripcion": producto.descripcion,
            "precio": str(producto.precio),
            "precio_oferta": str(producto.precio_oferta) if producto.precio_oferta is not None else None,
            "oferta_hasta": producto.oferta_hasta.isoformat() if producto.oferta_hasta else None,
            "stock": producto.stock,
            "activo": producto.activo,
            "destacado": producto.destacado,
            "oculto_por_admin": producto.oculto_por_admin,
            "motivo_ocultamiento": producto.motivo_ocultamiento,
            "imagen": copiar(producto.imagen),
            "fotos": [{"imagen": copiar(f.imagen), "orden": f.orden} for f in producto.fotos.all() if f.imagen],
        })

    datos = {
        "version": VERSION,
        "exportado": timezone.now().isoformat(timespec="seconds"),
        "tiendas": tiendas,
        "productos": productos,
    }
    (carpeta / "datos.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"tiendas": len(tiendas), "productos": len(productos), "faltantes": faltantes}


# ---------------------------------------------------------------------------
# Cargar
# ---------------------------------------------------------------------------

def _hora(texto):
    from datetime import time

    return time.fromisoformat(texto) if texto else None


def _asignar_imagen(campo, carpeta, ruta):
    """Asigna la imagen exportada al campo; al guardar, Django la pone en su carpeta de tienda."""
    if not ruta:
        return False
    origen = carpeta / "imagenes" / ruta
    if not origen.exists():
        return False
    with origen.open("rb") as contenido:
        campo.save(Path(ruta).name, File(contenido), save=False)
    return True


def cargar(carpeta=None, salida=print):
    """
    Crea las tiendas y productos de demo/datos.json que todavía no existan.
    Lo que ya existe (mismo usuario, nombre de tienda o WhatsApp) no se toca.
    """
    carpeta = Path(carpeta or carpeta_por_defecto())
    archivo = carpeta / "datos.json"
    if not archivo.exists():
        raise FileNotFoundError(
            f"No existe {archivo}. Primero ejecuta 'python manage.py exportar_demo' en la PC que tiene los datos "
            "y súbelo con git."
        )
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    resumen = {"tiendas": 0, "productos": 0, "omitidas": [], "admin_creado": False}
    grupo_tienda, _ = Group.objects.get_or_create(name="Tienda")
    tiendas_creadas = {}

    for t in datos.get("tiendas", []):
        conflicto = (
            User.objects.filter(username=t["usuario"]).exists()
            or Tienda.objects.filter(nombre=t["nombre"]).exists()
            or Tienda.objects.filter(whatsapp=t["whatsapp"]).exists()
        )
        if conflicto:
            resumen["omitidas"].append(t["nombre"])
            continue
        with transaction.atomic():
            usuario = User.objects.create_user(
                t["usuario"], correo_demo(t["usuario"]), CLAVE_DEMO,
                first_name=t.get("nombres", ""), last_name=t.get("apellidos", ""),
            )
            usuario.groups.add(grupo_tienda)
            tienda = Tienda(
                usuario=usuario, nombre=t["nombre"], direccion=t["direccion"], whatsapp=t["whatsapp"],
                descripcion=t.get("descripcion", ""), estado=t.get("estado", Tienda.Estado.ACTIVA),
                motivo_suspension=t.get("motivo_suspension", ""),
                verificada_en=timezone.now() if t.get("verificada") else None,
            )
            tienda.save()  # primero se guarda para tener número de carpeta
            if _asignar_imagen(tienda.logo, carpeta, t.get("logo")):
                tienda.save()
            for h in t.get("horarios", []):
                HorarioDia.objects.create(
                    tienda=tienda, dia=h["dia"], abre=_hora(h["abre"]), cierra=_hora(h["cierra"]),
                    descanso_inicio=_hora(h["descanso_inicio"]), descanso_fin=_hora(h["descanso_fin"]),
                )
        tiendas_creadas[t["nombre"]] = tienda
        resumen["tiendas"] += 1

    for p in datos.get("productos", []):
        tienda = tiendas_creadas.get(p["tienda"])
        if tienda is None:
            continue  # su tienda ya existía en esta PC: no se mezclan productos
        with transaction.atomic():
            categoria, _ = Categoria.objects.get_or_create(nombre=p["categoria"])
            marca, _ = Marca.objects.get_or_create(nombre=p["marca"])
            producto = Producto(
                tienda=tienda, categoria=categoria, marca=marca, nombre=p["nombre"],
                descripcion=p.get("descripcion", ""), precio=Decimal(p["precio"]),
                precio_oferta=Decimal(p["precio_oferta"]) if p.get("precio_oferta") else None,
                oferta_hasta=date.fromisoformat(p["oferta_hasta"]) if p.get("oferta_hasta") else None,
                stock=p.get("stock", 0), activo=p.get("activo", True), destacado=p.get("destacado", False),
                oculto_por_admin=p.get("oculto_por_admin", False),
                motivo_ocultamiento=p.get("motivo_ocultamiento", ""),
            )
            _asignar_imagen(producto.imagen, carpeta, p.get("imagen"))
            producto.save()
            for f in p.get("fotos", []):
                foto = FotoProducto(producto=producto, orden=f.get("orden", 0))
                if _asignar_imagen(foto.imagen, carpeta, f.get("imagen")):
                    foto.save()
        resumen["productos"] += 1

    # Si esta PC no tiene ningún administrador, se crea uno para poder entrar al panel.
    if not User.objects.filter(is_superuser=True).exists() and not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@demo.nexalys.pe", CLAVE_DEMO)
        resumen["admin_creado"] = True
    return resumen
