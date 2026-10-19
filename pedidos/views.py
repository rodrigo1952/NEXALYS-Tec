from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from tiendas.decorators import tienda_requerida

from .forms import FiltroPedidosForm, PedidoForm
from .models import Pedido
from .servicios import (
    OperacionNoPermitida,
    StockInsuficiente,
    actualizar_pedido,
    cambiar_estado,
    eliminar_pedido,
    registrar_pedido,
)

# Todas las vistas filtran por request.tienda: una tienda nunca ve pedidos de otra (404).


def _pedido_de_la_tienda(request, pk):
    return get_object_or_404(Pedido.objects.select_related("producto"), pk=pk, tienda=request.tienda)


@tienda_requerida()
def lista(request):
    pedidos = Pedido.objects.filter(tienda=request.tienda).select_related("producto")
    form = FiltroPedidosForm(request.GET or None)
    if form.is_valid():
        if form.cleaned_data["q"]:
            pedidos = pedidos.filter(cliente_nombre__icontains=form.cleaned_data["q"].strip())
        if form.cleaned_data["estado"]:
            pedidos = pedidos.filter(estado=form.cleaned_data["estado"])

    entregados = Pedido.objects.filter(tienda=request.tienda, estado=Pedido.Estado.ENTREGADO)
    resumen = entregados.aggregate(
        num_pedidos=Count("id"),
        ventas=Sum(
            ExpressionWrapper(
                F("precio_unitario") * F("cantidad"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        ),
    )
    pagina = Paginator(pedidos, 10).get_page(request.GET.get("page"))
    return render(request, "pedidos/lista.html", {"pagina": pagina, "form": form, "resumen": resumen})


@tienda_requerida()
def crear(request):
    form = PedidoForm(request.POST or None, tienda=request.tienda)
    if request.method == "POST" and form.is_valid():
        try:
            pedido = registrar_pedido(form.save(commit=False))
        except StockInsuficiente as error:
            form.add_error("cantidad", f"Stock insuficiente: {error}")
        else:
            messages.success(request, f"Pedido #{pedido.pk} registrado. Se descontó el stock del producto.")
            return redirect("pedidos:detalle", pk=pedido.pk)
    return render(request, "pedidos/form.html", {"form": form, "titulo": "Registrar pedido"})


@tienda_requerida()
def detalle(request, pk):
    pedido = _pedido_de_la_tienda(request, pk)
    return render(request, "pedidos/detalle.html", {"pedido": pedido})


@tienda_requerida()
def editar(request, pk):
    pedido = _pedido_de_la_tienda(request, pk)
    if not pedido.editable:
        messages.error(request, "Solo se pueden editar pedidos pendientes.")
        return redirect("pedidos:detalle", pk=pedido.pk)

    producto_anterior_id, cantidad_anterior = pedido.producto_id, pedido.cantidad
    form = PedidoForm(request.POST or None, instance=pedido, tienda=request.tienda)
    if request.method == "POST" and form.is_valid():
        try:
            actualizar_pedido(form.save(commit=False), producto_anterior_id, cantidad_anterior)
        except StockInsuficiente as error:
            form.add_error("cantidad", f"Stock insuficiente: {error}")
        except OperacionNoPermitida as error:
            messages.error(request, str(error))
            return redirect("pedidos:detalle", pk=pedido.pk)
        else:
            messages.success(request, f"Pedido #{pedido.pk} actualizado.")
            return redirect("pedidos:detalle", pk=pedido.pk)
    return render(
        request,
        "pedidos/form.html",
        {"form": form, "titulo": f"Editar pedido #{pedido.pk}", "pedido": pedido},
    )


@require_POST
@tienda_requerida()
def estado(request, pk):
    pedido = _pedido_de_la_tienda(request, pk)
    nuevo = request.POST.get("estado", "")
    try:
        cambiar_estado(pedido, nuevo)
    except OperacionNoPermitida as error:
        messages.error(request, str(error))
    else:
        texto = f"Pedido #{pedido.pk} marcado como {pedido.get_estado_display().lower()}."
        if nuevo == Pedido.Estado.CANCELADO:
            texto += " El stock fue restituido."
        messages.success(request, texto)
    return redirect("pedidos:detalle", pk=pedido.pk)


@tienda_requerida()
def eliminar(request, pk):
    pedido = _pedido_de_la_tienda(request, pk)
    if not pedido.eliminable:
        messages.error(
            request,
            "Los pedidos confirmados o entregados no se eliminan: forman parte del historial de ventas.",
        )
        return redirect("pedidos:detalle", pk=pedido.pk)
    if request.method == "POST":
        numero = pedido.pk
        try:
            eliminar_pedido(pedido)
        except OperacionNoPermitida as error:
            # Concurrencia: otra pestaña confirmó o eliminó el pedido mientras se veía esta página.
            messages.error(request, str(error))
            return redirect("pedidos:lista")
        messages.success(request, f"Pedido #{numero} eliminado.")
        return redirect("pedidos:lista")
    return render(request, "pedidos/confirmar_eliminar.html", {"pedido": pedido})
