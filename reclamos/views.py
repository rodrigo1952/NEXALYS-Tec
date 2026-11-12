"""
Libro de Reclamaciones virtual: el cliente llena la hoja, recibe su constancia por correo y la tienda
(o el administrador, si es contra NEXALYS Tec) la responde en máximo 15 días hábiles.
"""

import logging

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from administracion.acciones import registrar
from administracion.models import AccionAdmin
from cuentas import limites
from cuentas.privacidad import sumar_dias_habiles
from cuentas.views import rol_requerido, tiene_rol
from tiendas.decorators import tienda_requerida
from tiendas.models import Tienda

from .forms import ReclamoForm, RespuestaReclamoForm
from .models import PLAZO_DIAS_HABILES, Reclamo, datos_nexalys

logger = logging.getLogger(__name__)
solo_admin = rol_requerido("Administrador")
CLAVE_SESION = "hojas_presentadas"


def _enviar(asunto, texto, destinos):
    """Envía un correo; si falla, la hoja igual queda guardada (se anota el error)."""
    destinos = [d for d in destinos if d]
    if not destinos:
        return False
    try:
        send_mail(asunto, texto, None, destinos)
        return True
    except Exception:
        logger.exception("No se pudo enviar un correo del Libro de Reclamaciones")
        return False


# ---------------------------------------------------------------------------
# Público: llenar la hoja y ver la constancia
# ---------------------------------------------------------------------------

def libro(request):
    tienda_inicial = None
    if request.GET.get("tienda", "").isdigit():
        tienda_inicial = Tienda.objects.filter(pk=request.GET["tienda"], estado=Tienda.Estado.ACTIVA).first()
    form = ReclamoForm(request.POST or None, tienda_inicial=tienda_inicial, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        correo = form.cleaned_data["correo"]
        espera = limites.segundos_de_espera(limites.RECLAMO, request, correo)
        if espera:
            form.add_error(None, limites.mensaje_de_espera(espera))
        else:
            limites.anotar(limites.RECLAMO, request, correo)
            reclamo = form.save(commit=False)
            tienda = form.tienda_elegida
            proveedor = (
                {"nombre": tienda.nombre, "ruc": tienda.ruc, "direccion": tienda.direccion} if tienda else datos_nexalys()
            )
            reclamo.tienda = tienda
            reclamo.proveedor_nombre = proveedor["nombre"]
            reclamo.proveedor_ruc = proveedor["ruc"]
            reclamo.proveedor_direccion = proveedor["direccion"]
            reclamo.ip = limites.ip_de(request)
            reclamo.vence = sumar_dias_habiles(timezone.localdate(), PLAZO_DIAS_HABILES)
            reclamo.save()
            request.session[CLAVE_SESION] = request.session.get(CLAVE_SESION, []) + [reclamo.pk]
            _enviar(
                f"Constancia de tu hoja de reclamación N.° {reclamo.codigo} | NEXALYS Tec",
                render_to_string("reclamos/correo_constancia.txt", {"r": reclamo}),
                [reclamo.correo],
            )
            if tienda is not None:
                _enviar(
                    f"Tienes una hoja de reclamación nueva (N.° {reclamo.codigo}) | NEXALYS Tec",
                    render_to_string("reclamos/correo_aviso_tienda.txt", {"r": reclamo}),
                    [tienda.usuario.email],
                )
            return redirect("reclamos:hoja", pk=reclamo.pk)
    return render(request, "reclamos/libro.html", {"form": form, "plazo": PLAZO_DIAS_HABILES})


def _puede_ver(request, reclamo):
    if reclamo.pk in request.session.get(CLAVE_SESION, []):
        return True  # quien la presentó, en esta misma sesión
    usuario = request.user
    if not usuario.is_authenticated:
        return False
    if tiene_rol(usuario, "Administrador"):
        return True
    tienda = getattr(usuario, "tienda", None)
    return tienda is not None and reclamo.tienda_id == tienda.pk


def hoja(request, pk):
    """La hoja completa (constancia): para quien la presentó, la tienda reclamada y el administrador."""
    reclamo = get_object_or_404(Reclamo, pk=pk)
    if not _puede_ver(request, reclamo):
        raise PermissionDenied
    return render(request, "reclamos/hoja.html", {"r": reclamo, "recien_enviada": reclamo.pk in request.session.get(CLAVE_SESION, [])})


# ---------------------------------------------------------------------------
# Responder (tienda o administrador)
# ---------------------------------------------------------------------------

def _responder(request, reclamo, form):
    """Guarda la respuesta una sola vez y la envía al cliente. Devuelve True si se respondió ahora."""
    with transaction.atomic():
        reclamo = Reclamo.objects.select_for_update().get(pk=reclamo.pk)
        if reclamo.estado != Reclamo.Estado.PENDIENTE:
            messages.info(request, "Esta hoja ya fue respondida.")
            return False
        reclamo.estado = Reclamo.Estado.RESPONDIDO
        reclamo.respuesta = form.cleaned_data["respuesta"]
        reclamo.respondido_en = timezone.now()
        reclamo.respondido_por = request.user.get_username()
        reclamo.save()
        if tiene_rol(request.user, "Administrador"):
            registrar(request.user, AccionAdmin.Tipo.RESPONDER_RECLAMO, f"Hoja {reclamo.codigo} ({reclamo.proveedor_nombre})",
                      reclamo.respuesta)
    enviado = _enviar(
        f"Respuesta a tu hoja de reclamación N.° {reclamo.codigo} | NEXALYS Tec",
        render_to_string("reclamos/correo_respuesta.txt", {"r": reclamo}),
        [reclamo.correo],
    )
    if enviado:
        messages.success(request, f"Respuesta guardada y enviada a {reclamo.correo}.")
    else:
        messages.warning(request, f"Respuesta guardada, pero el correo no salió. Escríbele a {reclamo.correo}.")
    return True


@tienda_requerida(activa=False)
def tienda_lista(request):
    lista = Reclamo.objects.filter(tienda=request.tienda)
    return render(request, "reclamos/tienda_lista.html", {
        "pagina": Paginator(lista, 20).get_page(request.GET.get("page")),
        "pendientes": lista.filter(estado=Reclamo.Estado.PENDIENTE).count(),
        "plazo": PLAZO_DIAS_HABILES,
    })


@tienda_requerida(activa=False)
def tienda_detalle(request, pk):
    reclamo = get_object_or_404(Reclamo, pk=pk, tienda=request.tienda)
    form = RespuestaReclamoForm(request.POST or None)
    if request.method == "POST" and reclamo.estado == Reclamo.Estado.PENDIENTE and form.is_valid():
        _responder(request, reclamo, form)
        return redirect("reclamos:tienda_detalle", pk=pk)
    return render(request, "reclamos/tienda_detalle.html", {"r": reclamo, "form": form})


@solo_admin
def consola_lista(request):
    ver = request.GET.get("ver", "pendientes")
    lista = Reclamo.objects.select_related("tienda")
    if ver == "nexalys":
        lista = lista.filter(tienda=None, proveedor_clave="nexalys")
    elif ver != "todas":
        lista = lista.filter(estado=Reclamo.Estado.PENDIENTE)
    pendientes = Reclamo.objects.filter(estado=Reclamo.Estado.PENDIENTE)
    return render(request, "reclamos/consola_lista.html", {
        "pagina": Paginator(lista, 20).get_page(request.GET.get("page")),
        "ver": ver,
        "pendientes": pendientes.count(),
        "vencidas": pendientes.filter(vence__lt=timezone.localdate()).count(),
    })


@solo_admin
def consola_detalle(request, pk):
    """
    El administrador ve todas las hojas y responde las dirigidas a NEXALYS Tec (y las de una tienda
    que ya fue eliminada, para que ninguna quede sin respuesta).
    """
    reclamo = get_object_or_404(Reclamo.objects.select_related("tienda"), pk=pk)
    puede_responder = reclamo.proveedor_clave == "nexalys" or reclamo.tienda_id is None
    form = RespuestaReclamoForm(request.POST or None)
    if request.method == "POST":
        if not puede_responder:
            raise PermissionDenied  # las hojas de una tienda las responde la tienda
        if reclamo.estado == Reclamo.Estado.PENDIENTE and form.is_valid():
            _responder(request, reclamo, form)
            return redirect("reclamos:consola_detalle", pk=pk)
    return render(request, "reclamos/consola_detalle.html", {"r": reclamo, "form": form, "puede_responder": puede_responder})
