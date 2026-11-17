from datetime import timedelta

from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Case, Count, F, FloatField, IntegerField, Q, Value, When
from django.db.models.functions import Cast, Lower
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from catalogo.models import Categoria, Producto, precio_actual_expr
from tiendas.models import Tienda

from .models import DIAS_REPUESTO, ORDEN_POR_DEFECTO, ORDENES, Favorito, PreferenciaFavoritos
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


def _orden_elegido(request):
    """
    El orden de la dirección (?orden=…) si es válido, y se guarda como preferencia del cliente;
    si no viene, el que eligió la última vez (o «Recomendado»).
    """
    validos = dict(ORDENES)
    orden = request.GET.get("orden")
    if orden in validos:
        PreferenciaFavoritos.objects.update_or_create(usuario=request.user, defaults={"orden": orden})
        return orden
    guardado = PreferenciaFavoritos.objects.filter(usuario=request.user).values_list("orden", flat=True).first()
    return guardado if guardado in validos else ORDEN_POR_DEFECTO


def ordenar(favoritos, orden):
    """
    «Recomendado»: 1) bajaron de precio desde que se guardaron, 2) volvieron a tener stock o a estar
    publicados en los últimos 7 días, 3) todos los demás, 4) agotados o no disponibles. Dentro de cada grupo, el
    último agregado va primero.
    En los demás órdenes, los agotados y no disponibles también van al final: no sirve ver primero
    algo que no se puede comprar.
    """
    comprable = Q(producto__activo=True, producto__oculto_por_admin=False,
                  producto__tienda__estado="activa", producto__stock__gt=0)
    favoritos = favoritos.annotate(
        precio_actual=precio_actual_expr("producto__"),  # con la oferta, si hay una vigente
        al_final=Case(When(comprable, then=Value(0)), default=Value(1), output_field=IntegerField()),
    )
    if orden == "recomendado":
        limite = timezone.now() - timedelta(days=DIAS_REPUESTO)
        favoritos = favoritos.annotate(grupo=Case(
            When(al_final=1, then=Value(3)),
            When(precio_actual__lt=F("precio_guardado"), then=Value(0)),
            When(Q(producto__repuesto_el__gte=limite, producto__repuesto_el__gt=F("creado"))
                 | Q(producto__republicado_el__gte=limite, producto__republicado_el__gt=F("creado")), then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        ))
        return favoritos.order_by("grupo", "-creado", "-pk")
    if orden == "descuento":
        # Parte del precio normal que se paga hoy (0.7 = 30 % de descuento): menor, más descuento.
        # Con decimales: en SQLite «490 / 700» entre números enteros daría 0.
        favoritos = favoritos.annotate(parte_que_paga=Cast("precio_actual", FloatField()) / Cast("producto__precio", FloatField()))
    campos = {
        "recientes": ("-creado",),
        "nombre": (Lower("producto__nombre"),),
        "precio_asc": ("precio_actual",),
        "precio_desc": ("-precio_actual",),
        "descuento": ("parte_que_paga", "-creado"),
    }[orden]
    return favoritos.order_by("al_final", *campos, "-pk")


@cliente_requerido
def lista(request):
    """
    Mis favoritos, con la misma forma que el catálogo: filtros a la izquierda (categoría con su
    ícono y tienda, varias a la vez, con cuántos favoritos hay en cada una), «Ordenar por» (se
    recuerda para cada cliente) y tarjetas de producto.
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
    orden = _orden_elegido(request)
    pagina = Paginator(ordenar(favoritos, orden), 12).get_page(request.GET.get("page"))

    # Primero se calculan los avisos de lo que se muestra y luego se marca como
    # revisado, para que el contador del menú baje después de verlos.
    pagina.object_list = list(pagina.object_list)
    for favorito in pagina.object_list:
        favorito.aviso_disponible = favorito.republicado_reciente
        favorito.aviso_stock = not favorito.aviso_disponible and (favorito.volvio_a_tener_stock or favorito.repuesto_reciente)
        favorito.marcar_revisado()
    Favorito.objects.bulk_update(pagina.object_list, ["precio_visto", "agotado_visto"])

    return render(request, "favoritos/lista.html", {
        "pagina": pagina,
        "total": total,
        "categorias": categorias,
        "tiendas": tiendas,
        "hay_filtros": bool(categorias_elegidas or tiendas_elegidas),
        "orden": orden,
        "ordenes": ORDENES,
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
