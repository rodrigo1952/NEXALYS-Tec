import logging
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from catalogo.models import Producto
from favoritos.permisos import es_cliente

from .concurrencia import validar_y_guardar
from .forms import EliminarCuentaForm, PerfilForm, RegistroForm
from .models import DIAS_PARA_CONFIRMAR_CORREO, CorreoPendiente
from .verificacion import enviar_correo_confirmacion, horas_validez, leer_token

logger = logging.getLogger(__name__)


def tiene_rol(user, *roles):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=roles).exists()


def rol_requerido(*roles):
    """Permite el acceso solo a usuarios con alguno de los roles indicados."""
    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            if not tiene_rol(request.user, *roles):
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador


def inicio(request):
    visibles = Producto.objects.visibles().select_related("tienda", "marca", "categoria")
    return render(request, "inicio.html", {
        # Cada tienda elige hasta 3 destacados; primero los más populares de los últimos
        # 30 días (vistas + favoritos × 5) y, si empatan, el que se destacó antes.
        "destacados": visibles.destacados_inicio()[:8],
        # Ofertas: primero el mayor descuento.
        "ofertas": visibles.ofertas_inicio()[:8],
        "recientes": visibles[:8],
    })


def registro(request):
    if request.user.is_authenticated:
        return redirect("inicio")

    if request.method == "POST":
        form = RegistroForm(request.POST)
        # Regla de negocio: la cuenta queda inactiva hasta que el cliente confirme su correo.
        form.instance.is_active = False
        usuario = validar_y_guardar(form)
        if usuario:
            grupo, _ = Group.objects.get_or_create(name="Cliente")
            usuario.groups.add(grupo)
            CorreoPendiente.objects.create(usuario=usuario)
            _enviar_confirmacion(request, usuario)
            request.session["correo_por_confirmar"] = usuario.email
            return redirect("confirmacion_pendiente")
    else:
        form = RegistroForm()

    return render(request, "cuentas/registro.html", {"form": form})


def _enviar_confirmacion(request, usuario):
    try:
        enviar_correo_confirmacion(request, usuario)
        return True
    except Exception:  # p. ej. el servidor de correo no responde
        logger.exception("No se pudo enviar el correo de confirmación")
        messages.error(request, "No pudimos enviar el correo. Inténtalo de nuevo con el botón \"Reenviar enlace\".")
        return False


def _pagina_confirmacion(request, enlace_invalido=False, status=200):
    return render(request, "cuentas/confirmar_correo.html", {
        "correo": request.session.get("correo_por_confirmar", ""),
        "horas": horas_validez(),
        "dias": DIAS_PARA_CONFIRMAR_CORREO,
        "enlace_invalido": enlace_invalido,
    }, status=status)


def confirmacion_pendiente(request):
    """Después de registrarse: "Revisa tu correo", con opción de reenviar el enlace."""
    return _pagina_confirmacion(request)


@require_POST
def reenviar_confirmacion(request):
    correo = request.POST.get("email", "").strip()
    usuario = (
        User.objects.filter(email__iexact=correo, is_active=False, correo_pendiente__isnull=False).first()
        if correo else None
    )
    if usuario is not None:
        _enviar_confirmacion(request, usuario)
    request.session["correo_por_confirmar"] = correo
    # Mismo mensaje exista o no la cuenta: así no se revela qué correos están registrados.
    messages.info(request, "Si ese correo corresponde a una cuenta sin confirmar, te enviamos un enlace nuevo.")
    return redirect("confirmacion_pendiente")


def confirmar_correo(request, token):
    """El cliente abre el enlace del correo: su cuenta se activa y entra directamente."""
    usuario_id = leer_token(token)
    usuario = User.objects.filter(pk=usuario_id).first() if usuario_id else None
    if usuario is None:
        return _pagina_confirmacion(request, enlace_invalido=True, status=400)
    pendiente = CorreoPendiente.objects.filter(usuario=usuario).first()
    if pendiente is None:
        messages.info(request, "Tu correo ya estaba confirmado. Inicia sesión.")
        return redirect("login")
    usuario.is_active = True
    usuario.save(update_fields=["is_active"])
    pendiente.delete()
    request.session.pop("correo_por_confirmar", None)
    login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, "¡Correo confirmado! Bienvenido a NEXALYS Tec.")
    return redirect("inicio")


@login_required
def mi_cuenta(request):
    return render(request, "cuentas/mi_cuenta.html", {
        "puede_eliminar": _puede_eliminar_cuenta(request.user),
        "total_favoritos": request.user.favoritos.count(),
    })


@login_required
def editar_datos(request):
    form = PerfilForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Tus datos se actualizaron correctamente.")
        return redirect("mi_cuenta")
    return render(request, "cuentas/editar_datos.html", {"form": form})


def _puede_eliminar_cuenta(user):
    """
    Regla: solo los Clientes eliminan su cuenta desde la página. Una Tienda tiene
    productos y ventas, y el administrador no se elimina a sí mismo.
    """
    return es_cliente(user) and not user.is_superuser and getattr(user, "tienda", None) is None


@login_required
def eliminar_cuenta(request):
    """Ley de Protección de Datos Personales: el cliente puede borrar su cuenta y sus datos."""
    if not _puede_eliminar_cuenta(request.user):
        raise PermissionDenied

    form = EliminarCuentaForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = request.user
        logout(request)
        usuario.delete()  # también borra sus favoritos (CASCADE)
        messages.success(request, "Tu cuenta y tus datos fueron eliminados. ¡Gracias por usar NEXALYS Tec!")
        return redirect("inicio")
    return render(request, "cuentas/eliminar_cuenta.html", {"form": form})

