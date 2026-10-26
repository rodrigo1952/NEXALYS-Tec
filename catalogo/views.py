from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, ProtectedError, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from tiendas.decorators import tienda_requerida

from .forms import BusquedaForm, ProductoForm
from .models import Producto, VistaProducto

ORDENES = {
    "recientes": ("-creado",),
    # Se ordena por el precio que paga el cliente hoy (con la oferta, si hay una vigente).
    "precio_asc": ("precio_actual",),
    "precio_desc": ("-precio_actual",),
    "nombre": ("nombre",),
    # "Más relevantes" (opción vacía) cuando hay algo escrito en el buscador.
    "relevantes": ("-relevancia", "-creado"),
}


def _entero(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Catálogo público (CU-04 y CU-05): no requiere iniciar sesión
# ---------------------------------------------------------------------------

def catalogo(request):
    form = BusquedaForm(request.GET or None)
    productos = Producto.objects.visibles().con_precio_actual().select_related("tienda", "categoria", "marca")

    if form.is_valid():
        datos = form.cleaned_data
        if datos["q"]:
            # Sin tildes ni mayúsculas: "camara" encuentra "Cámara".
            # También busca en la descripción, pero con "Más relevantes" sale primero
            # lo que coincide en el nombre.
            productos = productos.buscar(datos["q"]).con_relevancia(datos["q"])
        if datos["solo_ofertas"]:
            productos = productos.en_oferta()
        if datos["categoria"]:
            productos = productos.filter(categoria=datos["categoria"])
        if datos["marca"]:
            productos = productos.filter(marca=datos["marca"])
        if datos["tienda"]:
            productos = productos.filter(tienda=datos["tienda"])
        if datos["precio_min"] is not None:
            productos = productos.filter(precio_actual__gte=datos["precio_min"])
        if datos["precio_max"] is not None:
            productos = productos.filter(precio_actual__lte=datos["precio_max"])
        orden = datos["orden"] or ("relevantes" if datos["q"] else "recientes")
        productos = productos.order_by(*ORDENES.get(orden, ORDENES["recientes"]))

    pagina = Paginator(productos, 12).get_page(request.GET.get("page"))
    return render(request, "catalogo/catalogo.html", {"form": form, "pagina": pagina})


def producto_detalle(request, pk):
    producto = get_object_or_404(
        Producto.objects.visibles()
        .select_related("tienda", "categoria", "marca")
        .prefetch_related("fotos", "tienda__horarios"),
        pk=pk,
    )
    relacionados = (
        Producto.objects.visibles()
        .filter(categoria=producto.categoria)
        .exclude(pk=producto.pk)
        .select_related("tienda")[:4]
    )
    # Se cuenta la visita para ordenar los destacados (1 por visitante al día).
    VistaProducto.registrar(request, producto)
    # Galería: la foto principal primero y luego las adicionales.
    fotos = [producto.imagen] if producto.imagen else []
    fotos += [foto.imagen for foto in producto.fotos.all()]
    return render(
        request,
        "catalogo/producto_detalle.html",
        {"producto": producto, "relacionados": relacionados, "fotos": fotos},
    )


# ---------------------------------------------------------------------------
# CRUD de productos de la tienda (CU-03): solo tiendas ACTIVAS
# Cada consulta se filtra por request.tienda, así una tienda nunca
# puede ver, editar ni eliminar productos de otra (responde 404).
# ---------------------------------------------------------------------------

@tienda_requerida()
def mis_productos(request):
    """
    "Mis productos" = catálogo + inventario en una sola sección (pestaña Productos).
    Muestra lo que ven los clientes (precio, publicado, destacado) junto con el stock,
    las alertas y los datos privados de la ficha de inventario.
    """
    bajo = Q(stock__gt=0, ficha__stock_minimo__gt=0, stock__lte=F("ficha__stock_minimo"))
    productos = (
        Producto.objects.filter(tienda=request.tienda)
        .select_related("categoria", "marca")
        # Privacidad: la tienda solo ve cuántos clientes guardaron el producto, no quiénes.
        .annotate(
            num_favoritos=Count("favoritos"),
            stock_minimo=Coalesce("ficha__stock_minimo", 0),
            costo=F("ficha__costo"),
            codigo=Coalesce("ficha__codigo", Value("")),
        )
        .order_by("-creado")  # orden fijo: así la paginación no repite ni salta productos
    )
    resumen = _resumen_inventario(request.tienda, bajo)
    solo_alertas = request.GET.get("alerta") == "1"
    if solo_alertas:
        productos = productos.filter(Q(stock=0) | bajo)
    texto = request.GET.get("q", "").strip()
    if texto:
        productos = productos.buscar(texto)

    # Cuántos productos tiene la tienda en cada categoría y marca (para los filtros).
    propios = Producto.objects.filter(tienda=request.tienda).order_by()
    categorias = (
        propios.values("categoria_id", "categoria__nombre")
        .annotate(cantidad=Count("id")).order_by("categoria__nombre")
    )
    categoria_id = _entero(request.GET.get("categoria"))
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)
        propios = propios.filter(categoria_id=categoria_id)  # las marcas se cuentan dentro de la categoría elegida
    marcas = propios.values("marca_id", "marca__nombre").annotate(cantidad=Count("id")).order_by("marca__nombre")
    marca_id = _entero(request.GET.get("marca"))
    if marca_id:
        productos = productos.filter(marca_id=marca_id)

    pagina = Paginator(productos, 10).get_page(request.GET.get("page"))
    return render(request, "catalogo/mis_productos.html", {
        "pagina": pagina, "q": texto, "resumen": resumen, "solo_alertas": solo_alertas,
        "categorias": categorias, "marcas": marcas,
        "categoria_id": categoria_id, "marca_id": marca_id,
        "total_productos": sum(c["cantidad"] for c in categorias),
    })


def _resumen_inventario(tienda, bajo):
    """Tarjetas de arriba: unidades, valor del inventario a costo, stock bajo y agotados."""
    datos = Producto.objects.filter(tienda=tienda).aggregate(
        productos=Count("id"),
        unidades=Coalesce(Sum("stock"), 0),
        valor=Sum(ExpressionWrapper(F("stock") * F("ficha__costo"), output_field=DecimalField(max_digits=14, decimal_places=2))),
        sin_costo=Count("id", filter=Q(stock__gt=0, ficha__costo__isnull=True)),
        agotados=Count("id", filter=Q(stock=0)),
        stock_bajo=Count("id", filter=bajo),
    )
    datos["valor"] = datos["valor"] or 0
    return datos


@tienda_requerida()
def producto_crear(request):
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, tienda=request.tienda)
        if form.is_valid():
            form.instance._usuario_cambio = request.user  # autor del "inventario inicial" en el kardex
            producto = form.save()
            messages.success(request, f"Producto \"{producto.nombre}\" registrado correctamente.")
            return redirect("catalogo:mis_productos")
    else:
        form = ProductoForm(tienda=request.tienda)
    return render(request, "catalogo/producto_form.html", {"form": form, "titulo": "Agregar producto"})


@tienda_requerida()
def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk, tienda=request.tienda)
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=producto, tienda=request.tienda)
        # La validación (incluida la versión) y el guardado van en una sola transacción,
        # para que nadie cambie el producto entre la comprobación y el guardado.
        with transaction.atomic():
            guardado = form.is_valid()
            if guardado:
                form.instance._usuario_cambio = request.user  # por si cambió el stock (kardex)
                form.save()
        if guardado:
            messages.success(request, f"Producto \"{producto.nombre}\" actualizado.")
            return redirect("catalogo:mis_productos")
    else:
        form = ProductoForm(instance=producto, tienda=request.tienda)
    return render(
        request,
        "catalogo/producto_form.html",
        {"form": form, "titulo": "Editar producto", "producto": producto},
    )


@tienda_requerida()
def producto_eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk, tienda=request.tienda)
    # Regla de negocio: un producto con pedidos no se elimina, para conservar el historial de ventas.
    if producto.pedidos.exists():
        messages.error(
            request,
            f"No se puede eliminar \"{producto.nombre}\" porque tiene pedidos registrados. "
            "Puedes ocultarlo desmarcando \"publicado\".",
        )
        return redirect("catalogo:mis_productos")
    if request.method == "POST":
        nombre = producto.nombre
        try:
            with transaction.atomic():
                producto.delete()  # el modelo borra la imagen solo si la eliminación se confirma
        except ProtectedError:
            # Concurrencia: se registró un pedido de este producto mientras se confirmaba la eliminación.
            messages.error(
                request,
                f"No se puede eliminar \"{nombre}\" porque se le acaba de registrar un pedido. "
                "Puedes ocultarlo desmarcando \"publicado\".",
            )
            return redirect("catalogo:mis_productos")
        messages.success(request, f"Producto \"{nombre}\" eliminado.")
        return redirect("catalogo:mis_productos")
    return render(request, "catalogo/producto_confirmar_eliminar.html", {"producto": producto})
