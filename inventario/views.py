"""
Inventario de la tienda: fichas, kardex, proveedores, ventas, ingresos, ajustes y conteo físico.

Todo se filtra por request.tienda: una tienda nunca ve ni modifica el inventario
de otra (responde 404). Los costos y proveedores son privados de cada tienda.
"""

from datetime import timedelta

from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from catalogo.models import Categoria, Producto
from tiendas.decorators import tienda_requerida

from . import reportes, servicios
from .forms import (
    AjusteForm, AnularIngresoForm, AnularVentaForm, FichaForm, IngresoForm, LineasIngresoFormSet,
    LineasVentaFormSet, ProveedorForm, VentaForm,
)
from .kardex import ficha_de
from .models import FichaInventario, Ingreso, LineaIngreso, LineaVenta, Movimiento, Proveedor, Venta


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


def _producto_elegido(request):
    """?producto=ID (al volver de crear un producto): queda elegido en la primera fila."""
    pk = request.GET.get("producto", "")
    if request.method == "POST" or not pk.isdigit():
        return None
    if not Producto.objects.filter(pk=pk, tienda=request.tienda).exists():
        return None
    return [{"producto": int(pk)}]


@tienda_requerida()
def venta_nueva(request):
    datos = request.POST if request.method == "POST" else None
    form = VentaForm(datos)
    lineas = LineasVentaFormSet(datos, initial=_producto_elegido(request),
                                form_kwargs={"tienda": request.tienda}, prefix="lineas")
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


# ---------------------------------------------------------------------------
# Ingresos de mercadería (Etapa 3)
# ---------------------------------------------------------------------------

def _periodo(request):
    periodo = request.GET.get("periodo", "mes")
    return periodo if periodo in dict(PERIODOS) else "mes"


@tienda_requerida()
def ingresos(request):
    periodo = _periodo(request)
    lista = Ingreso.objects.filter(tienda=request.tienda).prefetch_related("lineas")
    desde = desde_periodo(periodo)
    if desde:
        lista = lista.filter(fecha__date__gte=desde)
    texto = request.GET.get("q", "").strip()
    if texto:
        filtro = (Q(proveedor_nombre__icontains=texto) | Q(documento__icontains=texto)
                  | Q(lineas__producto_nombre__icontains=texto))
        if texto.isdigit():
            filtro |= Q(numero=int(texto))
        lista = lista.filter(filtro).distinct()
    validos = lista.filter(anulado=False)
    resumen = validos.aggregate(total=Sum("total"), cantidad=Count("id", distinct=True))
    resumen["unidades"] = LineaIngreso.objects.filter(ingreso__in=validos).aggregate(u=Sum("cantidad"))["u"] or 0
    pagina = Paginator(lista.order_by("-fecha", "-id"), 20).get_page(request.GET.get("page"))
    return render(request, "inventario/ingresos.html", {
        "pagina": pagina, "q": texto, "periodo": periodo, "periodos": PERIODOS, "resumen": resumen,
    })


@tienda_requerida()
def ingreso_nuevo(request):
    datos = request.POST if request.method == "POST" else None
    form = IngresoForm(datos, tienda=request.tienda)
    lineas = LineasIngresoFormSet(datos, initial=_producto_elegido(request),
                                  form_kwargs={"tienda": request.tienda}, prefix="lineas")
    if datos is not None and form.is_valid() and lineas.is_valid():
        recibidas = [
            servicios.LineaRecibida(f.cleaned_data["producto"].pk, f.cleaned_data["cantidad"], f.cleaned_data["costo"])
            for f in lineas.forms if f.cleaned_data.get("producto")
        ]
        try:
            ingreso = servicios.registrar_ingreso(request.tienda, request.user, recibidas, **form.cleaned_data)
        except servicios.OperacionNoPermitida as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, f"Ingreso N.° {servicios.numero_ingreso(ingreso)} registrado. "
                                      "El stock y el costo promedio se actualizaron.")
            return redirect("inventario:ingreso_detalle", pk=ingreso.pk)
    return render(request, "inventario/ingreso_form.html", {"form": form, "lineas": lineas, "visibles": 3})


def _ingreso_propio(request, pk):
    return get_object_or_404(Ingreso.objects.prefetch_related("lineas"), pk=pk, tienda=request.tienda)


@tienda_requerida()
def ingreso_detalle(request, pk):
    return render(request, "inventario/ingreso_detalle.html", {"ingreso": _ingreso_propio(request, pk)})


@tienda_requerida()
def ingreso_anular(request, pk):
    ingreso = _ingreso_propio(request, pk)
    if ingreso.anulado:
        messages.info(request, "Este ingreso ya estaba anulado.")
        return redirect("inventario:ingreso_detalle", pk=ingreso.pk)
    form = AnularIngresoForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            servicios.anular_ingreso(ingreso, request.user, form.cleaned_data["motivo"])
        except servicios.OperacionNoPermitida as error:
            messages.error(request, str(error))
        else:
            messages.warning(request, f"Ingreso N.° {servicios.numero_ingreso(ingreso)} anulado. "
                                      "Su stock se restó y su costo salió del promedio.")
        return redirect("inventario:ingreso_detalle", pk=ingreso.pk)
    return render(request, "inventario/ingreso_anular.html", {"ingreso": ingreso, "form": form})


# ---------------------------------------------------------------------------
# Ajustes y conteo físico (Etapa 3)
# ---------------------------------------------------------------------------

TIPOS_AJUSTE = [("", "Ajustes y conteos"), ("ajuste", "Solo ajustes"), ("conteo", "Solo conteos")]


@tienda_requerida()
def ajustes(request):
    """Historial de ajustes y conteos físicos de la tienda."""
    periodo = _periodo(request)
    tipo = request.GET.get("tipo", "")
    tipos = [tipo] if tipo in ("ajuste", "conteo") else [Movimiento.Tipo.AJUSTE, Movimiento.Tipo.CONTEO]
    lista = Movimiento.objects.filter(tienda=request.tienda, tipo__in=tipos).select_related("usuario")
    desde = desde_periodo(periodo)
    if desde:
        lista = lista.filter(fecha__date__gte=desde)
    texto = request.GET.get("q", "").strip()
    if texto:
        lista = lista.filter(Q(producto_nombre__icontains=texto) | Q(nota__icontains=texto))
    pagina = Paginator(lista, 25).get_page(request.GET.get("page"))
    return render(request, "inventario/ajustes.html", {
        "pagina": pagina, "q": texto, "periodo": periodo, "periodos": PERIODOS,
        "tipo": tipo if tipo in ("ajuste", "conteo") else "", "tipos": TIPOS_AJUSTE,
    })


@tienda_requerida()
def ajuste_nuevo(request):
    datos = request.POST if request.method == "POST" else None
    inicial = {}
    if datos is None and request.GET.get("producto", "").isdigit():
        inicial["producto"] = request.GET["producto"]
    form = AjusteForm(datos, initial=inicial, tienda=request.tienda)
    if datos is not None and form.is_valid():
        motivo, cantidad = form.motivo_y_cantidad()
        producto = form.cleaned_data["producto"]
        try:
            servicios.registrar_ajuste(request.tienda, request.user, producto.pk, motivo, cantidad,
                                       form.cleaned_data["nota"])
        except (servicios.StockInsuficiente, servicios.OperacionNoPermitida) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, f"Ajuste registrado: {producto.nombre} {cantidad:+d}.")
            return redirect("inventario:ajustes")
    return render(request, "inventario/ajuste_form.html", {"form": form})


MAX_PRODUCTOS_CONTEO = 300  # Django acepta hasta 1000 campos por formulario (2 por producto)


@tienda_requerida()
def conteo(request):
    """
    Conteo físico: la tienda escribe lo que contó en el local y se corrigen los
    productos con diferencia. Las casillas vacías no se tocan.
    """
    productos = Producto.objects.filter(tienda=request.tienda).select_related("categoria").annotate(
        codigo=F("ficha__codigo")
    ).order_by("nombre")
    categorias = Categoria.objects.filter(productos__tienda=request.tienda).distinct().order_by("nombre")
    categoria_id = request.GET.get("categoria", "")
    if categoria_id.isdigit():
        productos = productos.filter(categoria_id=categoria_id)
    texto = request.GET.get("q", "").strip()
    if texto:
        productos = productos.filter(Q(nombre__icontains=texto) | Q(ficha__codigo__icontains=texto))
    total = productos.count()
    productos = list(productos[:MAX_PRODUCTOS_CONTEO])

    escritos, errores = {}, {}
    if request.method == "POST":
        conteos = []
        for clave, valor in request.POST.items():
            if not clave.startswith("contado_") or not valor.strip():
                continue
            pk = clave.removeprefix("contado_")
            visto = request.POST.get(f"visto_{pk}", "")
            if not pk.isdigit():
                continue
            escritos[int(pk)] = valor
            if not valor.strip().isdigit() or not visto.isdigit():
                errores[int(pk)] = "Escribe un número entero (0 o más)."
                continue
            conteos.append(servicios.Contado(int(pk), int(valor), int(visto)))
        if not escritos:
            messages.error(request, "No escribiste ninguna cantidad contada.")
        elif not errores:
            resultado = servicios.registrar_conteo(request.tienda, request.user, conteos,
                                                   request.POST.get("nota", "")[:120])
            corregidos = len(resultado.corregidos)
            messages.success(
                request, f"Conteo guardado: {corregidos} producto{'s' if corregidos != 1 else ''} corregido"
                         f"{'s' if corregidos != 1 else ''} y {resultado.sin_diferencia} sin diferencia."
            )
            if resultado.cambiaron:
                messages.warning(
                    request, "El stock de " + ", ".join(resultado.cambiaron) + " cambió mientras contabas "
                    "(una venta u otro movimiento). No se corrigió: vuelve a contarlo."
                )
                return redirect(request.get_full_path())
            return redirect(f"{reverse('inventario:ajustes')}?tipo=conteo")

    filas = [{"producto": p, "escrito": escritos.get(p.pk, ""), "error": errores.get(p.pk)} for p in productos]
    return render(request, "inventario/conteo.html", {
        "filas": filas, "categorias": categorias, "categoria_id": categoria_id, "q": texto,
        "total": total, "limite": MAX_PRODUCTOS_CONTEO,
    })


# ---------------------------------------------------------------------------
# Resumen y reportes (Etapa 4)
# ---------------------------------------------------------------------------

def _datos_resumen(request):
    rango, error = reportes.rango_desde_get(request.GET)
    tienda = request.tienda
    productos, inventario = reportes.inventario_valorizado(tienda)
    return {
        "rango": rango, "error_rango": error, "periodos": reportes.PERIODOS_RESUMEN,
        "ventas": reportes.resumen_ventas(tienda, rango),
        "serie": reportes.ventas_en_el_tiempo(tienda, rango),
        "metodos": reportes.por_metodo_de_pago(tienda, rango),
        "mas_vendidos": reportes.mas_vendidos(tienda, rango),
        "inventario": inventario, "productos_valorizados": productos,
        "sin_movimiento": reportes.sin_movimiento(tienda),
        "dias_sin_movimiento": reportes.DIAS_SIN_MOVIMIENTO,
        "alertas": reportes.alertas_de_stock(tienda),
    }


@tienda_requerida()
def resumen(request):
    datos = _datos_resumen(request)
    if datos["error_rango"]:
        messages.error(request, datos["error_rango"])
    datos["sin_movimiento_vista"] = datos["sin_movimiento"][:10]
    datos["alertas_vista"] = datos["alertas"][:10]
    datos["grafico"] = {
        "etiquetas": datos["serie"]["etiquetas"], "vendido": datos["serie"]["vendido"],
        "ganancia": datos["serie"]["ganancia"],
        "metodos": [m["metodo"] for m in datos["metodos"]],
        "metodos_suma": [float(m["suma"]) for m in datos["metodos"]],
    }
    return render(request, "inventario/resumen.html", datos)


@tienda_requerida()
def resumen_excel(request):
    try:
        from .excel import libro_de_reportes
    except ImportError:
        messages.error(request, "Para descargar en Excel falta instalar openpyxl: "
                                "ejecuta «pip install -r requirements.txt» y vuelve a intentarlo.")
        return redirect(f"{reverse('inventario:resumen')}?{request.GET.urlencode()}")
    datos = _datos_resumen(request)
    libro = libro_de_reportes(request.tienda, datos)
    rango = datos["rango"]
    nombre = f"reporte_{slugify(request.tienda.nombre) or 'tienda'}_{rango.desde:%Y%m%d}_{rango.hasta:%Y%m%d}.xlsx"
    respuesta = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    libro.save(respuesta)
    return respuesta
