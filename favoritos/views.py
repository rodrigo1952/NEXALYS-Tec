from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Count
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


def _enteros(valores):
    """Lista de números válidos (sin repetidos) a partir de lo que llega en la dirección."""
    return list(dict.fromkeys(n for n in (_entero(v) for v in valores) if n))


@cliente_requerido
def lista(request):
    """
    Mis favoritos, con la misma forma que el catálogo: filtros a la izquierda (categoría con su
    ícono y tienda, varias a la vez, con cuántos favoritos hay en cada una) y tarjetas de producto.
    """
    favoritos = (
        Favorito.objects.filter(usuario=request.user)
        .select_related("producto__tienda", "producto__categoria", "producto__marca")
    )
    total = favoritos.count()

    categorias_elegidas = _enteros(request.GET.getlist("categoria"))
    tiendas_elegidas = _enteros(request.GET.getlist("tienda"))
    por_categoria = favoritos.filter(producto__categoria_id__in=categorias_elegidas) if categorias_elegidas else favoritos
    por_tienda = favoritos.filter(producto__tienda_id__in=tiendas_elegidas) if tiendas_elegidas else favoritos

    # Cada opción muestra cuántos favoritos tiene, contando con los otros filtros ya puestos
    # (así se pueden sumar varias categorías o tiendas a la vez).
    categorias = [
        {"pk": c.pk, "nombre": c.nombre, "icono": c.icono or "grid", "cantidad": c.cantidad,
         "elegida": c.pk in categorias_elegidas}
        for c in Categoria.objects.filter(productos__favoritos__in=por_tienda)
        .annotate(cantidad=Count("productos__favoritos", distinct=True)).order_by("nombre")
    ]
    tiendas = [
        {"pk": t.pk, "nombre": t.nombre, "cantidad": t.cantidad, "elegida": t.pk in tiendas_elegidas}
        for t in Tienda.objects.filter(productos__favoritos__in=por_categoria)
        .annotate(cantidad=Count("productos__favoritos", distinct=True)).order_by("nombre")
    ]

    favoritos = por_categoria
    if tiendas_elegidas:
        favoritos = favoritos.filter(producto__tienda_id__in=tiendas_elegidas)
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
        "hay_filtros": bool(categorias_elegidas or tiendas_elegidas),
    })


@require_POST
@cliente_requerido
def alternar(request, pk):
    """
    El corazón: si el producto ya está en favoritos lo quita; si no, lo guarda.

    Si el clic llega desde JavaScript (cabecera X-Requested-With), responde con
    JSON y la página NO se recarga: el usuario se queda en el mismo lugar.
    Sin JavaScript funciona igual que antes: guarda y vuelve a la página de origen.
    """
    favorito = Favorito.objects.filter(usuario=request.user, producto_id=pk).select_related("producto").first()
    if favorito:
        nombre = favorito.producto.nombre
        favorito.delete()
        guardado, mensaje = False, f"Quitaste \"{nombre}\" de tus favoritos."
    else:
        # Solo se pueden guardar productos que se ven en el catálogo.
        producto = get_object_or_404(Producto.objects.visibles(), pk=pk)
        Favorito.guardar(request.user, producto)
        guardado, mensaje = True, f"Guardaste \"{producto.nombre}\" en tus favoritos."

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"guardado": guardado, "mensaje": mensaje})

    (messages.success if guardado else messages.info)(request, mensaje)
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
