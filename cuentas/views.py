from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from catalogo.models import Producto
from favoritos.permisos import es_cliente

from .concurrencia import validar_y_guardar
from .forms import EliminarCuentaForm, PerfilForm, RegistroForm


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
    recientes = Producto.objects.visibles().select_related("tienda", "marca")[:8]
    return render(request, "inicio.html", {"recientes": recientes})


def registro(request):
    if request.user.is_authenticated:
        return redirect("inicio")

    if request.method == "POST":
        form = RegistroForm(request.POST)
        usuario = validar_y_guardar(form)
        if usuario:
            grupo, _ = Group.objects.get_or_create(name="Cliente")
            usuario.groups.add(grupo)
            login(request, usuario)
            messages.success(request, "¡Bienvenido! Tu cuenta fue creada correctamente.")
            return redirect("inicio")
    else:
        form = RegistroForm()

    return render(request, "cuentas/registro.html", {"form": form})


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
    productos y pedidos, y el administrador no se elimina a sí mismo.
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


@rol_requerido("Administrador")
def panel_admin(request):
    return render(request, "cuentas/panel_admin.html")
