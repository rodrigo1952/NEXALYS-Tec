import logging

from django.contrib import messages
from django.contrib.auth import login
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalogo.models import Producto

from .decorators import tienda_requerida
from .forms import RegistroTiendaForm
from .models import Tienda
from .verificacion import enviar_correo_verificacion, leer_token

logger = logging.getLogger(__name__)


def _enviar_verificacion(request, tienda):
    """Envía el correo y avisa al usuario si falló (flujo alternativo del CU-01)."""
    try:
        enviar_correo_verificacion(request, tienda)
    except Exception:  # p. ej. el servidor de correo no responde
        logger.exception("No se pudo enviar el correo de verificación")
        messages.warning(
            request,
            "No pudimos enviar el correo de verificación. Inténtalo de nuevo desde tu panel.",
        )
        return False
    return True


def registro_tienda(request):
    """CU-01 Registrar tienda."""
    if request.user.is_authenticated:
        messages.info(request, "Cierra sesión para registrar una nueva tienda.")
        return redirect("inicio")

    if request.method == "POST":
        form = RegistroTiendaForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                usuario = form.save()
            login(request, usuario)
            if _enviar_verificacion(request, usuario.tienda):
                messages.success(
                    request,
                    f"¡Tienda registrada! Te enviamos un enlace a {usuario.email} "
                    "para verificar tu correo y activar tu tienda.",
                )
            return redirect("tiendas:panel")
    else:
        form = RegistroTiendaForm()

    return render(request, "tiendas/registro_tienda.html", {"form": form})


def verificar(request, token):
    """Activa la tienda cuando el propietario abre el enlace del correo."""
    tienda_id = leer_token(token)
    tienda = Tienda.objects.filter(pk=tienda_id).first() if tienda_id else None
    if tienda is None:
        return render(request, "tiendas/verificacion_invalida.html", status=400)

    if tienda.estado == Tienda.Estado.SUSPENDIDA:
        messages.error(request, "Tu tienda está suspendida. Comunícate con el administrador.")
    elif tienda.marcar_verificada():
        messages.success(request, "¡Correo verificado! Tu tienda ya está activa y puede publicar productos.")
    else:
        messages.info(request, "Tu correo ya había sido verificado.")

    if request.user.is_authenticated and request.user.pk == tienda.usuario_id:
        return redirect("tiendas:panel")
    return redirect("login")


@require_POST
@tienda_requerida(activa=False)
def reenviar_verificacion(request):
    tienda = request.tienda
    if tienda.estado != Tienda.Estado.PENDIENTE:
        messages.info(request, "Tu tienda no necesita verificación.")
    elif _enviar_verificacion(request, tienda):
        messages.success(request, f"Te enviamos un nuevo enlace a {request.user.email}.")
    return redirect("tiendas:panel")


@tienda_requerida(activa=False)
def panel(request):
    tienda = request.tienda
    productos = Producto.objects.filter(tienda=tienda)
    contexto = {
        "tienda": tienda,
        "total_productos": productos.count(),
        "publicados": productos.filter(activo=True).count(),
        "agotados": productos.filter(stock=0).count(),
    }
    return render(request, "tiendas/panel.html", contexto)


def perfil(request, pk):
    """CU-06 Consultar ubicación de tienda: perfil público con dirección y productos."""
    tienda = get_object_or_404(Tienda, pk=pk, estado=Tienda.Estado.ACTIVA)
    productos = (
        Producto.objects.visibles()
        .filter(tienda=tienda)
        .select_related("categoria", "marca", "tienda")
    )
    return render(request, "tiendas/perfil.html", {"tienda": tienda, "productos": productos})
