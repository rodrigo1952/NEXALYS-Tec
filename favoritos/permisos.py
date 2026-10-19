from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def es_cliente(user):
    return user.is_authenticated and user.groups.filter(name="Cliente").exists()


def cliente_requerido(vista):
    """Regla de negocio: solo los Clientes tienen favoritos (las tiendas reciben 403)."""

    @wraps(vista)
    @login_required
    def envoltura(request, *args, **kwargs):
        if not es_cliente(request.user):
            raise PermissionDenied
        return vista(request, *args, **kwargs)

    return envoltura
