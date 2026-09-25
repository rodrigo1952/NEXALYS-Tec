from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from .forms import RegistroForm


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
    return render(request, "inicio.html")


def registro(request):
    if request.user.is_authenticated:
        return redirect("inicio")

    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
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
    return render(request, "cuentas/mi_cuenta.html")


@rol_requerido("Administrador")
def panel_admin(request):
    return render(request, "cuentas/panel_admin.html")


@rol_requerido("Administrador", "Vendedor")
def panel_vendedor(request):
    return render(request, "cuentas/panel_vendedor.html")