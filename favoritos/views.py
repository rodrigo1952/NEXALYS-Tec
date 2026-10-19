from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from catalogo.models import Categoria, Producto
from tiendas.models import Tienda

from .models import Favorito
from .permisos import cliente_requerido
from .signals import CLAVE_SESION


def _entero(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _destino_seguro(request, por_defecto):
    """Vuelve a la página desde donde se tocó el corazón (solo si es de este sitio)."""
    destino = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return destino
    return por_defecto


@cliente_requerido
def lista(request):
    """Mis favoritos: precio y stock actuales, avisos, WhatsApp y filtros."""
    favoritos = (
        Favorito.objects.filter(usuario=request.user)
        .select_related("producto__tienda", "producto__categoria", "producto__marca")
    )
    total = favoritos.count()

    # Las opciones de los filtros salen solo de los productos guardados.
    categorias = Categoria.objects.filter(productos__favoritos__usuario=request.user).distinct()
    tiendas = Tienda.objects.filter(productos__favoritos__usuario=request.user).distinct()

    categoria_id = _entero(request.GET.get("categoria"))
    tienda_id = _entero(request.GET.get("tienda"))
    if categoria_id:
        favoritos = favoritos.filter(producto__categoria_id=categoria_id)
    if tienda_id:
        favoritos = favoritos.filter(producto__tienda_id=tienda_id)

    pagina = Paginator(favoritos, 12).get_page(request.GET.get("page"))

    # Primero se calculan los avisos de lo que se muestra y luego se marca como
    # revisado, para que el contador del menú baje después de verlos.
    pagina.object_list = list(pagina.object_list)
    for favorito in pagina.object_list:
        favorito.aviso_stock = favorito.volvio_a_tener_stock
        favorito.marcar_revisado()
    Favorito.objects.bulk_update(pagina.object_list, ["precio_visto", "agotado_visto"])

    return render(request, "favoritos/lista.html", {
        "pagina": pagina,
        "total": total,
        "categorias": categorias,
        "tiendas": tiendas,
        "categoria_id": categoria_id,
        "tienda_id": tienda_id,
    })


@require_POST
@cliente_requerido
def alternar(request, pk):
    """El corazón: si el producto ya está en favoritos lo quita; si no, lo guarda."""
    favorito = Favorito.objects.filter(usuario=request.user, producto_id=pk).select_related("producto").first()
    if favorito:
        nombre = favorito.producto.nombre
        favorito.delete()
        messages.info(request, f"Quitaste \"{nombre}\" de tus favoritos.")
    else:
        # Solo se pueden guardar productos que se ven en el catálogo.
        producto = get_object_or_404(Producto.objects.visibles(), pk=pk)
        Favorito.guardar(request.user, producto)
        messages.success(request, f"Guardaste \"{producto.nombre}\" en tus favoritos.")
    return redirect(_destino_seguro(request, reverse("favoritos:lista")))


def guardar_despues(request, pk):
    """
    Corazón tocado por un visitante sin sesión: recordamos el producto y lo
    enviamos a iniciar sesión. Al entrar, la señal lo guarda automáticamente.
    """
    producto = get_object_or_404(Producto.objects.visibles(), pk=pk)
    detalle = reverse("catalogo:detalle", args=[producto.pk])
    if request.user.is_authenticated:
        return redirect(detalle)

    request.session[CLAVE_SESION] = producto.pk
    messages.info(request, "Inicia sesión o crea tu cuenta de cliente para guardar este producto.")
    return redirect(f"{reverse('login')}?next={detalle}")
