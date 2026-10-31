from math import ceil, floor

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Max, Min, Q, Sum, Value
from django.db.models.functions import Coalesce, Lower
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

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

FILTROS = ("q", "categoria", "marca", "tienda", "precio_min", "precio_max", "solo_ofertas", "en_stock")
MARCAS_VISIBLES = 8  # las demás marcas se muestran con «Ver todas»


def _filtrar(productos, datos, excepto=()):
    """Aplica los filtros del catálogo; `excepto` deja fuera algunos (para contar las opciones de ese filtro)."""
    if datos.get("q") and "q" not in excepto:
        # Sin tildes ni mayúsculas: "camara" encuentra "Cámara". También busca en la descripción,
        # pero con "Más relevantes" sale primero lo que coincide en el nombre.
        productos = productos.buscar(datos["q"]).con_relevancia(datos["q"])
    if datos.get("categoria") and "categoria" not in excepto:
        productos = productos.filter(categoria=datos["categoria"])
    if datos.get("marca") and "marca" not in excepto:
        productos = productos.filter(marca__in=datos["marca"])
    if datos.get("tienda") and "tienda" not in excepto:
        productos = productos.filter(tienda__in=datos["tienda"])
    if datos.get("solo_ofertas") and "solo_ofertas" not in excepto:
        productos = productos.en_oferta()
    if datos.get("en_stock") and "en_stock" not in excepto:
        productos = productos.filter(stock__gt=0)
    if "precio" not in excepto:
        if datos.get("precio_min") is not None:
            productos = productos.filter(precio_actual__gte=datos["precio_min"])
        if datos.get("precio_max") is not None:
            productos = productos.filter(precio_actual__lte=datos["precio_max"])
    return productos


def _sin(request, clave, valor=None):
    """Enlace a la misma página sin un filtro (o sin uno de sus valores, p. ej. una marca)."""
    consulta = request.GET.copy()
    consulta.pop("page", None)
    if valor is None:
        consulta.pop(clave, None)
    else:
        consulta.setlist(clave, [v for v in consulta.getlist(clave) if v != str(valor)])
    if clave == "precio_min":
        consulta.pop("precio_max", None)  # el precio se quita completo (desde y hasta)
    return f"{request.path}?{consulta.urlencode()}" if consulta else request.path


def _opciones(productos, campo, nombre, elegidos):
    """Opciones de un filtro con su cantidad de productos; las elegidas siempre se muestran."""
    filas = productos.order_by().values(campo, nombre).annotate(cantidad=Count("id"))
    opciones = {f[campo]: {"pk": f[campo], "nombre": f[nombre], "cantidad": f["cantidad"]} for f in filas}
    for objeto in elegidos:
        opciones.setdefault(objeto.pk, {"pk": objeto.pk, "nombre": str(objeto), "cantidad": 0})
    ids = {objeto.pk for objeto in elegidos}
    lista = sorted(opciones.values(), key=lambda o: (o["nombre"].lower() in ("otra", "otros"), o["nombre"].lower()))
    for opcion in lista:
        opcion["elegida"] = opcion["pk"] in ids
    return lista


def catalogo(request):
    """
    CU-04 y CU-05. Filtros a la izquierda (disponibilidad, precio, marca y tienda, con cuántos
    productos tiene cada opción) que se aplican al instante. La categoría se elige en la barra de
    categorías y la búsqueda en el buscador del menú: aquí se muestran como título y «chips».
    """
    form = BusquedaForm(request.GET or None)
    base = Producto.objects.visibles().con_precio_actual().select_related("tienda", "categoria", "marca")
    datos = form.cleaned_data if form.is_valid() else {}

    productos = _filtrar(base, datos)
    orden = datos.get("orden") or ("relevantes" if datos.get("q") else "recientes")
    productos = productos.order_by(*ORDENES.get(orden, ORDENES["recientes"]))
    pagina = Paginator(productos, 12).get_page(request.GET.get("page"))

    # Cada filtro cuenta sus opciones con los DEMÁS filtros aplicados.
    marcas = _opciones(_filtrar(base, datos, {"marca"}), "marca_id", "marca__nombre", datos.get("marca") or [])
    tiendas = _opciones(_filtrar(base, datos, {"tienda"}), "tienda_id", "tienda__nombre", datos.get("tienda") or [])
    rango = _filtrar(base, datos, {"precio"}).aggregate(minimo=Min("precio_actual"), maximo=Max("precio_actual"))
    precio = {
        "minimo": int(floor(rango["minimo"])) if rango["minimo"] is not None else 0,
        "maximo": int(ceil(rango["maximo"])) if rango["maximo"] is not None else 0,
    }
    disponibilidad = {
        "en_stock": _filtrar(base, datos, {"en_stock"}).filter(stock__gt=0).count(),
        "ofertas": _filtrar(base, datos, {"solo_ofertas"}).en_oferta().count(),
    }

    # Filtros elegidos, cada uno con su enlace para quitarlo.
    chips = []
    if datos.get("q"):
        chips.append({"texto": f"Búsqueda: «{datos['q']}»", "url": _sin(request, "q")})
    if datos.get("categoria"):
        chips.append({"texto": datos["categoria"].nombre, "url": _sin(request, "categoria")})
    for marca in datos.get("marca") or []:
        chips.append({"texto": marca.nombre, "url": _sin(request, "marca", marca.pk)})
    for tienda in datos.get("tienda") or []:
        chips.append({"texto": tienda.nombre, "url": _sin(request, "tienda", tienda.pk)})
    if datos.get("precio_min") is not None or datos.get("precio_max") is not None:
        desde = f"S/ {datos['precio_min']:,.2f}" if datos.get("precio_min") is not None else "S/ 0.00"
        hasta = f"S/ {datos['precio_max']:,.2f}" if datos.get("precio_max") is not None else "más"
        chips.append({"texto": f"{desde} – {hasta}", "url": _sin(request, "precio_min")})
    if datos.get("en_stock"):
        chips.append({"texto": "En stock", "url": _sin(request, "en_stock")})
    if datos.get("solo_ofertas"):
        chips.append({"texto": "🔥 Ofertas", "url": _sin(request, "solo_ofertas")})

    if datos.get("categoria"):
        titulo = datos["categoria"].nombre
    elif datos.get("q"):
        titulo = f"Resultados para «{datos['q']}»"
    else:
        titulo = "Todos los productos"

    return render(request, "catalogo/catalogo.html", {
        "form": form, "pagina": pagina, "titulo": titulo, "chips": chips,
        "marcas": marcas, "marcas_visibles": MARCAS_VISIBLES, "tiendas": tiendas,
        "precio": precio, "disponibilidad": disponibilidad,
        "precio_min": datos.get("precio_min"), "precio_max": datos.get("precio_max"),
    })


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
        .order_by(Lower("nombre"), "pk")  # A → Z; el pk deja el orden fijo para la paginación
    )
    resumen = _resumen_inventario(request.tienda, bajo)
    # Filtros rápidos (reemplazan a las tarjetas: los números están en la pestaña Resumen).
    ver = request.GET.get("ver", "")
    if request.GET.get("alerta") == "1":
        ver = "alertas"  # enlaces antiguos y "Ver las alertas" del Resumen
    elif request.GET.get("sin_costo") == "1":
        ver = "sin_costo"
    filtros = {
        "alertas": Q(stock=0) | bajo,
        "bajo": bajo,
        "agotados": Q(stock=0),
        "sin_costo": Q(ficha__costo__isnull=True),
    }
    if ver in filtros:
        productos = productos.filter(filtros[ver])
    else:
        ver = ""
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
        "pagina": pagina, "q": texto, "resumen": resumen, "ver": ver,
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
        sin_costo=Count("id", filter=Q(ficha__costo__isnull=True)),
        agotados=Count("id", filter=Q(stock=0)),
        stock_bajo=Count("id", filter=bajo),
    )
    datos["valor"] = datos["valor"] or 0
    return datos


# Desde "Nuevo ingreso" o "Nueva venta" se puede crear un producto que aún no existe:
# al guardarlo se vuelve a esa página con el producto ya elegido.
VOLVER_A = {"ingreso": "inventario:ingreso_nuevo", "venta": "inventario:venta_nueva"}


@tienda_requerida()
def producto_crear(request):
    volver = request.GET.get("volver") if request.GET.get("volver") in VOLVER_A else ""
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, tienda=request.tienda)
        if form.is_valid():
            form.instance._usuario_cambio = request.user  # autor del "inventario inicial" en el kardex
            producto = form.save()
            messages.success(request, f"Producto \"{producto.nombre}\" registrado correctamente.")
            if volver:
                return redirect(f"{reverse(VOLVER_A[volver])}?producto={producto.pk}")
            return redirect("catalogo:mis_productos")
    else:
        form = ProductoForm(tienda=request.tienda)
    return render(request, "catalogo/producto_form.html", {
        "form": form, "titulo": "Agregar producto", "volver": volver,
        "url_cancelar": reverse(VOLVER_A[volver]) if volver else reverse("catalogo:mis_productos"),
    })


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
    # Sus ventas, ingresos y kardex NO se borran: guardan el nombre del producto (historial).
    if request.method == "POST":
        nombre = producto.nombre
        with transaction.atomic():
            producto.delete()  # el modelo borra la imagen solo si la eliminación se confirma
        messages.success(request, f"Producto \"{nombre}\" eliminado.")
        return redirect("catalogo:mis_productos")
    return render(request, "catalogo/producto_confirmar_eliminar.html", {"producto": producto})
