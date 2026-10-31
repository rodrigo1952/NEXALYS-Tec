import logging

from django.contrib import messages
from django.contrib.auth import login
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from catalogo.models import Producto
from cuentas.concurrencia import validar_y_guardar
from cuentas.reautenticacion import confirmada_recientemente, marcar_confirmada

from .decorators import tienda_requerida
from .forms import HORAS_SUGERIDAS, EditarTiendaForm, LogoForm, RegistroTiendaForm, horario_formset
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
        usuario = validar_y_guardar(form)  # usuario y tienda se guardan juntos o no se guarda nada
        if usuario:
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
        # Privacidad: solo cantidades, nunca quiénes guardaron cada producto.
        "mas_guardados": (
            productos.annotate(num_favoritos=Count("favoritos"))
            .filter(num_favoritos__gt=0)
            .order_by("-num_favoritos", "nombre")[:5]
        ),
    }
    return render(request, "tiendas/panel.html", contexto)


@tienda_requerida(activa=False)
def editar(request):
    """La tienda edita sus datos, su logo y su horario de atención."""
    tienda = request.tienda
    form = EditarTiendaForm(
        request.POST or None, request.FILES or None, instance=tienda, prefix="datos",
        usuario=request.user, ya_confirmada=confirmada_recientemente(request),
    )
    # Si el formulario llega sin la parte del horario (p. ej. desde otra página), el horario no se toca.
    con_horario = request.method != "POST" or "horario-TOTAL_FORMS" in request.POST
    horario = horario_formset(request.POST if request.method == "POST" and con_horario else None, tienda)
    if request.method == "POST":
        datos_validos = form.is_valid()  # se validan los dos para mostrar todos los errores
        horario_valido = horario.is_valid() if con_horario else True
        if datos_validos and horario_valido:
            try:
                with transaction.atomic():  # datos y horario se guardan juntos o nada
                    form.save()
                    if con_horario:
                        horario.save(tienda)
            except IntegrityError:
                # Concurrencia: otra tienda tomó el mismo nombre o WhatsApp en este instante.
                form.add_error(None, "Otra tienda acaba de registrar ese nombre o WhatsApp. Revisa los datos.")
            else:
                if form.clave_confirmada:
                    marcar_confirmada(request)
                messages.success(request, "Los datos de tu tienda se actualizaron correctamente.")
                return redirect("tiendas:panel")
    return render(request, "tiendas/editar.html", {
        "form": form, "horario": horario, "tienda": tienda, "horas_sugeridas": HORAS_SUGERIDAS,
    })


@require_POST
@tienda_requerida(activa=False)
def cambiar_logo(request):
    """Cambia o quita el logo desde el círculo del menú de la cuenta (ventana con vista previa)."""
    tienda = request.tienda
    destino = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        destino = reverse("tiendas:panel")
    if request.POST.get("quitar"):
        if tienda.logo:
            tienda.logo = None
            tienda.save()
            messages.success(request, "Quitaste el logo de tu tienda.")
        return redirect(destino)
    form = LogoForm(request.POST, request.FILES, instance=tienda)
    if form.is_valid() and form.cleaned_data.get("logo"):
        form.save()
        messages.success(request, "¡Listo! Tu tienda ya tiene el logo nuevo.")
    else:
        errores = [e for lista in form.errors.values() for e in lista] or ["Elige una imagen."]
        messages.error(request, "No se pudo cambiar el logo: " + " ".join(errores))
    return redirect(destino)


def perfil(request, pk):
    """CU-06 Consultar ubicación de tienda: perfil público con dirección y productos."""
    tienda = get_object_or_404(
        Tienda.objects.prefetch_related("horarios"), pk=pk, estado=Tienda.Estado.ACTIVA
    )
    productos = (
        Producto.objects.visibles()
        .filter(tienda=tienda)
        .select_related("categoria", "marca", "tienda")
        .order_by(Lower("nombre"), "pk")  # A → Z
    )
    return render(request, "tiendas/perfil.html", {"tienda": tienda, "productos": productos})
