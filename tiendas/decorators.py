from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .models import Tienda


def tienda_requerida(activa=True):
    """
    Protege las vistas de las tiendas.

    - Si el usuario no inició sesión, lo envía al login.
    - Si el usuario no tiene una tienda, responde 403.
    - Si activa=True y la tienda no está ACTIVA (pendiente o suspendida),
      lo regresa a su panel con un aviso. Regla de negocio: solo las tiendas
      con correo verificado y no suspendidas pueden gestionar productos.

    La tienda queda disponible en la vista como request.tienda.
    """

    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            tienda = getattr(request.user, "tienda", None)
            if tienda is None:
                raise PermissionDenied
            if activa and tienda.estado != Tienda.Estado.ACTIVA:
                if tienda.estado == Tienda.Estado.SUSPENDIDA:
                    messages.error(
                        request,
                        "Tu tienda está suspendida. Comunícate con el administrador.",
                    )
                else:
                    messages.warning(
                        request,
                        "Primero verifica tu correo para poder gestionar productos.",
                    )
                return redirect("tiendas:panel")
            request.tienda = tienda
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador
