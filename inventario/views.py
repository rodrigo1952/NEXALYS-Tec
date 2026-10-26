"""
Sección Inventario de la tienda (Etapa 1: productos con su ficha, kardex y proveedores).

Todo se filtra por request.tienda: una tienda nunca ve ni modifica el inventario
de otra (responde 404). Los costos y proveedores son privados de cada tienda.
"""

from datetime import timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from catalogo.models import Producto
from tiendas.decorators import tienda_requerida

from . import servicios
from .forms import AnularVentaForm, FichaForm, LineasVentaFormSet, ProveedorForm, VentaForm
from .kardex import ficha_de
from .models import FichaInventario, LineaVenta, Proveedor, Venta


@tienda_requerida()
def inicio(request):
    # El inventario vive dentro de "Mis productos" (catálogo + inventario en una sola sección).
    return redirect("catalogo:mis_productos")


def _ficha_o_vacia(producto):
    """La ficha guardada o una vacía (sin crearla en la base de datos solo por mirar la lista)."""
    try:
        return producto.ficha
    except FichaInventario.DoesNotExist:
        return FichaInventario(producto=producto)


@tienda_requerida()
def productos(request):
    """La lista de productos con su stock está en "Mis productos"."""
    return redirect("catalogo:mis_productos")


def _producto_propio(request, pk):
    return get_object_or_404(Producto.objects.select_related("tienda"), pk=pk, tienda=request.tienda)


@tienda_requerida()
def ficha(request, pk):
    producto = _producto_propio(request, pk)
    form = FichaForm(request.POST or None, instance=ficha_de(producto), tienda=request.tienda)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Se guardó la ficha de inventario de \"{producto.nombre}\".")
        return redirect("catalogo:mis_productos")
    return render(request, "inventario/ficha_form.html", {"form": form, "producto": producto})


@tienda_requerida()
def kardex(request, pk):
    producto = _producto_propio(request, pk)
    movimientos = producto.movimientos.select_related("usuario", "venta", "ingreso").order_by("-fecha", "-id")
    pagina = Paginator(movimientos, 25).get_page(request.GET.get("page"))
    return render(request, "inventario/kardex.html", {
        "producto": producto, "ficha": _ficha_o_vacia(producto), "pagina": pagina,
    })


@tienda_requerida()
def proveedores(request):
    lista = Proveedor.objects.filter(tienda=request.tienda)
    texto = request.GET.get("q", "").strip()
    if texto:
        lista = lista.filter(nombre__icontains=texto) | lista.filter(ruc__icontains=texto)
    pagina = Paginator(lista.order_by("nombre"), 20).get_page(request.GET.get("page"))
    return render(request, "inventario/proveedores.html", {"pagina": pagina, "q": texto})


@tienda_requerida()
def proveedor_crear(request):
    form = ProveedorForm(request.POST or None, tienda=request.tienda)
    if request.method == "POST" and form.is_valid():
        proveedor = form.save()
        messages.success(request, f"Proveedor \"{proveedor}\" registrado.")
        return redirect("inventario:proveedores")
    return render(request, "inventario/proveedor_form.html", {"form": form, "titulo": "Nuevo proveedor"})


@tienda_requerida()
def proveedor_editar(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk, tienda=request.tienda)
    form = ProveedorForm(request.POST or None, instance=proveedor, tienda=request.tienda)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Proveedor \"{proveedor}\" actualizado.")
        return redirect("inventario:proveedores")
    return render(request, "inventario/proveedor_form.html", {"form": form, "titulo": "Editar proveedor"})


@tienda_requerida()
def proveedor_eliminar(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk, tienda=request.tienda)
    if request.method == "POST":
        nombre = str(proveedor)
        proveedor.delete()  # sus ingresos se conservan con el nombre del proveedor
        messages.success(request, f"Proveedor \"{nombre}\" eliminado.")
        return redirect("inventario:proveedores")
    return render(request, "inventario/proveedor_eliminar.html", {
        "proveedor": proveedor, "num_ingresos": proveedor.ingresos.count(),
    })


# ---------------------------------------------------------------------------
# Ventas (Etapa 2)
# ---------------------------------------------------------------------------

PERIODOS = [("hoy", "Hoy"), ("semana", "Últimos 7 días"), ("mes", "Este mes"), ("todo", "Todas")]


def desde_periodo(periodo):
    """Primer día del periodo (None = sin límite)."""
    hoy = timezone.localdate()
    return {"hoy": hoy, "semana": hoy - timedelta(days=6), "mes": hoy.replace(day=1)}.get(periodo)


@tienda_requerida()
def ventas(request):
    periodo = request.GET.get("periodo", "mes")
    if periodo not in dict(PERIODOS):
        periodo = "mes"
    lista = Venta.objects.filter(tienda=request.tienda).prefetch_related("lineas")
    desde = desde_periodo(periodo)
    if desde:
        lista = lista.filter(fecha__date__gte=desde)
    texto = request.GET.get("q", "").strip()
    if texto:
        filtro = Q(cliente_nombre__icontains=texto) | Q(cliente_documento__icontains=texto) | Q(lineas__producto_nombre__icontains=texto)
        if texto.isdigit():
            filtro |= Q(numero=int(texto))
        lista = lista.filter(filtro).distinct()

    validas = lista.filter(anulada=False)
    resumen = validas.aggregate(total=Sum("total"), cantidad=Count("id", distinct=True))
    resumen["unidades"] = LineaVenta.objects.filter(venta__in=validas).aggregate(u=Sum("cantidad"))["u"] or 0
    por_metodo = [
        (Venta.MetodoPago(fila["metodo_pago"]).label, fila["suma"])
        for fila in validas.order_by().values("metodo_pago").annotate(suma=Sum("total")).order_by("-suma")
    ]
    pagina = Paginator(lista.order_by("-fecha", "-id"), 20).get_page(request.GET.get("page"))
    return render(request, "inventario/ventas.html", {
        "pagina": pagina, "q": texto, "periodo": periodo, "periodos": PERIODOS,
        "resumen": resumen, "por_metodo": por_metodo,
    })


@tienda_requerida()
def venta_nueva(request):
    datos = request.POST if request.method == "POST" else None
    form = VentaForm(datos)
    lineas = LineasVentaFormSet(datos, form_kwargs={"tienda": request.tienda}, prefix="lineas")
    if datos is not None and form.is_valid() and lineas.is_valid():
        pedidas = [
            servicios.LineaPedida(f.cleaned_data["producto"].pk, f.cleaned_data["cantidad"], f.cleaned_data.get("precio"))
            for f in lineas.forms if f.cleaned_data.get("producto")
        ]
        try:
            venta = servicios.registrar_venta(request.tienda, request.user, pedidas, **form.cleaned_data)
        except (servicios.StockInsuficiente, servicios.OperacionNoPermitida) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, f"Venta N.° {servicios.numero_venta(venta)} registrada. El stock se actualizó.")
            return redirect("inventario:venta_detalle", pk=venta.pk)
    return render(request, "inventario/venta_form.html", {"form": form, "lineas": lineas, "visibles": 3})


def _venta_propia(request, pk):
    return get_object_or_404(Venta.objects.prefetch_related("lineas"), pk=pk, tienda=request.tienda)


@tienda_requerida()
def venta_detalle(request, pk):
    """La venta como "nota de venta" lista para imprimir."""
    return render(request, "inventario/venta_detalle.html", {"venta": _venta_propia(request, pk), "tienda": request.tienda})


@tienda_requerida()
def venta_anular(request, pk):
    venta = _venta_propia(request, pk)
    if venta.anulada:
        messages.info(request, "Esta venta ya estaba anulada.")
        return redirect("inventario:venta_detalle", pk=venta.pk)
    form = AnularVentaForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            servicios.anular_venta(venta, request.user, form.cleaned_data["motivo"])
        except servicios.OperacionNoPermitida as error:
            messages.error(request, str(error))
        else:
            messages.warning(request, f"Venta N.° {servicios.numero_venta(venta)} anulada. El stock de sus productos volvió.")
        return redirect("inventario:venta_detalle", pk=venta.pk)
    return render(request, "inventario/venta_anular.html", {"venta": venta, "form": form})
