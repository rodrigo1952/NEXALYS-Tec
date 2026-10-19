from django.db.models import F, Q

from .models import Favorito
from .permisos import es_cliente


def favoritos(request):
    """
    Para el menú y las tarjetas de producto:
    - ids_favoritos: productos que el cliente ya guardó (corazón lleno).
    - avisos_favoritos: favoritos que bajaron de precio o volvieron a tener
      stock desde la última vez que abrió "Mis favoritos".
    """
    user = getattr(request, "user", None)
    if not user or not es_cliente(user):
        return {"ids_favoritos": set(), "avisos_favoritos": 0}

    mios = Favorito.objects.filter(usuario=user)
    avisos = (
        mios.filter(producto__activo=True, producto__tienda__estado="activa")
        .filter(
            Q(producto__precio__lt=F("precio_visto"))
            | Q(agotado_visto=True, producto__stock__gt=0)
        )
        .count()
    )
    return {
        "ids_favoritos": set(mios.values_list("producto_id", flat=True)),
        "avisos_favoritos": avisos,
    }
