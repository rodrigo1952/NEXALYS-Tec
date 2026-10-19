"""
Panel de administración con el diseño de NEXALYS (rol Administrador).

Reemplaza el uso diario de Django Admin: resumen, tiendas, productos, pedidos y
usuarios. Categorías y marcas siguen en catalogo/gestion.py. Django Admin queda
como herramienta avanzada.
"""

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, ProtectedError, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from catalogo.models import Categoria, Marca, Producto, borrar_archivo_al_confirmar
from cuentas.views import rol_requerido
from pedidos.models import Pedido
from tiendas.models import Tienda

from .forms import EliminarUsuarioForm, MotivoForm

solo_admin = rol_requerido("Administrador")

TOTAL_PEDIDO = ExpressionWrapper(
    F("precio_unitario") * F("cantidad"),
    output_field=DecimalField(max_digits=12, decimal_places=2),
)


def _entero(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _volver(request, por_defecto):
    """Regresa a la página anterior (solo si es de este sitio)."""
    destino = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return redirect(destino)
    return redirect(por_defecto)


# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------

@solo_admin
def resumen(request):
    inicio_mes = timezone.localdate().replace(day=1)
    estados = dict(Tienda.objects.order_by().values_list("estado").annotate(n=Count("id")))
    pedidos_mes = Pedido.objects.filter(creado__date__gte=inicio_mes)
    ventas_mes = pedidos_mes.filter(estado=Pedido.Estado.ENTREGADO).aggregate(total=Sum(TOTAL_PEDIDO))["total"]
    return render(request, "cuentas/panel_admin.html", {
        "tiendas_activas": estados.get(Tienda.Estado.ACTIVA, 0),
        "tiendas_pendientes": estados.get(Tienda.Estado.PENDIENTE, 0),
        "tiendas_suspendidas": estados.get(Tienda.Estado.SUSPENDIDA, 0),
        "productos_publicados": Producto.objects.visibles().count(),
        "productos_ocultos": Producto.objects.filter(oculto_por_admin=True).count(),
        "clientes": User.objects.filter(groups__name="Cliente").count(),
        "pedidos_mes": pedidos_mes.count(),
        "ventas_mes": ventas_mes or 0,
        "categorias": Categoria.objects.count(),
        "marcas": Marca.objects.count(),
    })


# ---------------------------------------------------------------------------
# Tiendas
# ---------------------------------------------------------------------------

@solo_admin
def tiendas(request):
    lista = Tienda.objects.select_related("usuario").annotate(
        num_productos=Count("productos", distinct=True),
        num_pedidos=Count("pedidos", distinct=True),
    )
    estado = request.GET.get("estado", "")
    texto = request.GET.get("q", "").strip()
    if estado in Tienda.Estado.values:
        lista = lista.filter(estado=estado)
    if texto:
        lista = lista.filter(
            Q(nombre__icontains=texto) | Q(usuario__username__icontains=texto)
            | Q(usuario__email__icontains=texto) | Q(whatsapp__icontains=texto)
        )
    pagina = Paginator(lista, 15).get_page(request.GET.get("page"))
    return render(request, "administracion/tiendas.html", {
        "pagina": pagina, "estado": estado, "q": texto, "estados": Tienda.Estado.choices,
    })


@solo_admin
def tienda_detalle(request, pk):
    tienda = get_object_or_404(Tienda.objects.select_related("usuario").prefetch_related("horarios"), pk=pk)
    productos = tienda.productos.all()
    return render(request, "administracion/tienda_detalle.html", {
        "tienda": tienda,
        "form": MotivoForm(),
        "total_productos": productos.count(),
        "publicados": productos.filter(activo=True, oculto_por_admin=False).count(),
        "ocultos_admin": productos.filter(oculto_por_admin=True).count(),
        "total_pedidos": tienda.pedidos.count(),
    })


@require_POST
@solo_admin
def tienda_suspender(request, pk):
    tienda = get_object_or_404(Tienda, pk=pk)
    form = MotivoForm(request.POST)
    if form.is_valid():
        tienda.suspender(form.cleaned_data["motivo"])
        messages.warning(request, f"La tienda \"{tienda}\" fue suspendida; sus productos ya no se ven en el catálogo.")
        return redirect("administracion:tienda_detalle", pk=tienda.pk)
    # Se vuelve a mostrar el detalle con el error del motivo.
    productos = tienda.productos.all()
    return render(request, "administracion/tienda_detalle.html", {
        "tienda": tienda, "form": form,
        "total_productos": productos.count(),
        "publicados": productos.filter(activo=True, oculto_por_admin=False).count(),
        "ocultos_admin": productos.filter(oculto_por_admin=True).count(),
        "total_pedidos": tienda.pedidos.count(),
    }, status=400)


@require_POST
@solo_admin
def tienda_reactivar(request, pk):
    tienda = get_object_or_404(Tienda, pk=pk)
    tienda.reactivar()
    if tienda.estado == Tienda.Estado.ACTIVA:
        messages.success(request, f"La tienda \"{tienda}\" fue reactivada.")
    else:
        messages.info(request, f"\"{tienda}\" quedó pendiente: aún debe verificar su correo para activarse.")
    return redirect("administracion:tienda_detalle", pk=tienda.pk)


# ---------------------------------------------------------------------------
# Productos (el administrador ve y oculta; no edita: los datos son de cada tienda)
# ---------------------------------------------------------------------------

ESTADOS_PRODUCTO = [
    ("publicado", "Publicados"),
    ("oculto_tienda", "Ocultos por la tienda"),
    ("oculto_admin", "Ocultos por el administrador"),
]


@solo_admin
def productos(request):
    lista = Producto.objects.select_related("tienda", "categoria", "marca")
    tienda_id = _entero(request.GET.get("tienda"))
    categoria_id = _entero(request.GET.get("categoria"))
    estado = request.GET.get("estado", "")
    texto = request.GET.get("q", "").strip()
    if tienda_id:
        lista = lista.filter(tienda_id=tienda_id)
    if categoria_id:
        lista = lista.filter(categoria_id=categoria_id)
    if estado == "publicado":
        lista = lista.filter(activo=True, oculto_por_admin=False)
    elif estado == "oculto_tienda":
        lista = lista.filter(activo=False)
    elif estado == "oculto_admin":
        lista = lista.filter(oculto_por_admin=True)
    if texto:
        lista = lista.buscar(texto)
    pagina = Paginator(lista, 20).get_page(request.GET.get("page"))
    return render(request, "administracion/productos.html", {
        "pagina": pagina, "q": texto, "estado": estado, "estados": ESTADOS_PRODUCTO,
        "tienda_id": tienda_id, "categoria_id": categoria_id,
        "tiendas": Tienda.objects.all(), "categorias": Categoria.objects.all(),
    })


@solo_admin
def producto_ocultar(request, pk):
    producto = get_object_or_404(Producto.objects.select_related("tienda"), pk=pk)
    form = MotivoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        producto.oculto_por_admin = True
        producto.motivo_ocultamiento = form.cleaned_data["motivo"].strip()
        producto.save(update_fields=["oculto_por_admin", "motivo_ocultamiento", "actualizado"])
        messages.warning(request, f"\"{producto}\" ya no se ve en el catálogo. La tienda verá el motivo.")
        return redirect("administracion:productos")
    return render(request, "administracion/producto_ocultar.html", {"producto": producto, "form": form})


@require_POST
@solo_admin
def producto_mostrar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    producto.oculto_por_admin = False
    producto.motivo_ocultamiento = ""
    producto.save(update_fields=["oculto_por_admin", "motivo_ocultamiento", "actualizado"])
    messages.success(request, f"\"{producto}\" vuelve a mostrarse (si la tienda lo tiene publicado).")
    return _volver(request, "administracion:productos")


# ---------------------------------------------------------------------------
# Pedidos (solo consulta)
# ---------------------------------------------------------------------------

@solo_admin
def pedidos(request):
    lista = Pedido.objects.select_related("tienda", "producto")
    tienda_id = _entero(request.GET.get("tienda"))
    estado = request.GET.get("estado", "")
    texto = request.GET.get("q", "").strip()
    if tienda_id:
        lista = lista.filter(tienda_id=tienda_id)
    if estado in Pedido.Estado.values:
        lista = lista.filter(estado=estado)
    if texto:
        lista = lista.filter(Q(cliente_nombre__icontains=texto) | Q(producto__nombre__icontains=texto))
    entregados = lista.filter(estado=Pedido.Estado.ENTREGADO)
    resumen_ventas = entregados.aggregate(num_entregados=Count("id"), total=Sum(TOTAL_PEDIDO))
    pagina = Paginator(lista, 20).get_page(request.GET.get("page"))
    return render(request, "administracion/pedidos.html", {
        "pagina": pagina, "q": texto, "estado": estado, "estados": Pedido.Estado.choices,
        "tienda_id": tienda_id, "tiendas": Tienda.objects.all(),
        "total_pedidos": lista.count(),
        "entregados": resumen_ventas["num_entregados"],
        "ventas": resumen_ventas["total"] or 0,
    })


# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------

def rol_de(usuario):
    nombres = {g.name for g in usuario.groups.all()}
    if usuario.is_superuser or "Administrador" in nombres:
        return "Administrador"
    if getattr(usuario, "tienda", None) is not None:
        return "Tienda"
    if "Cliente" in nombres:
        return "Cliente"
    return "Sin rol"


def _motivo_no_se_puede_modificar(admin, usuario):
    """Regla: el administrador no se cambia a sí mismo ni a otros administradores."""
    if usuario.pk == admin.pk:
        return "No puedes desactivar ni eliminar tu propia cuenta."
    if rol_de(usuario) == "Administrador":
        return "Las cuentas de administrador no se modifican desde aquí."
    return None


@solo_admin
def usuarios(request):
    lista = User.objects.select_related("tienda").prefetch_related("groups").order_by("-date_joined")
    rol = request.GET.get("rol", "")
    estado = request.GET.get("estado", "")
    texto = request.GET.get("q", "").strip()
    if rol == "cliente":
        lista = lista.filter(groups__name="Cliente")
    elif rol == "tienda":
        lista = lista.filter(tienda__isnull=False)
    elif rol == "administrador":
        lista = lista.filter(Q(is_superuser=True) | Q(groups__name="Administrador"))
    if estado == "activo":
        lista = lista.filter(is_active=True)
    elif estado == "inactivo":
        lista = lista.filter(is_active=False)
    if texto:
        lista = lista.filter(
            Q(username__icontains=texto) | Q(email__icontains=texto)
            | Q(first_name__icontains=texto) | Q(last_name__icontains=texto)
        )
    pagina = Paginator(lista.distinct(), 20).get_page(request.GET.get("page"))
    pagina.object_list = list(pagina.object_list)
    for usuario in pagina.object_list:
        usuario.rol = rol_de(usuario)
        usuario.protegido = _motivo_no_se_puede_modificar(request.user, usuario) is not None
    return render(request, "administracion/usuarios.html", {
        "pagina": pagina, "q": texto, "rol": rol, "estado": estado,
    })


@require_POST
@solo_admin
def usuario_estado(request, pk):
    """Activa o desactiva una cuenta. Una cuenta desactivada no puede iniciar sesión."""
    usuario = get_object_or_404(User, pk=pk)
    motivo = _motivo_no_se_puede_modificar(request.user, usuario)
    if motivo:
        messages.error(request, motivo)
        return _volver(request, "administracion:usuarios")
    usuario.is_active = not usuario.is_active
    usuario.save(update_fields=["is_active"])
    if usuario.is_active:
        messages.success(request, f"La cuenta \"{usuario}\" fue reactivada.")
    else:
        texto = f"La cuenta \"{usuario}\" fue desactivada: ya no puede iniciar sesión."
        if getattr(usuario, "tienda", None) is not None:
            texto += " Sus productos siguen visibles; si quieres ocultarlos, suspende también la tienda."
        messages.warning(request, texto)
    return _volver(request, "administracion:usuarios")


@solo_admin
def usuario_eliminar(request, pk):
    usuario = get_object_or_404(User.objects.select_related("tienda"), pk=pk)
    motivo = _motivo_no_se_puede_modificar(request.user, usuario)
    tienda = getattr(usuario, "tienda", None)
    if not motivo and tienda is not None and tienda.pedidos.exists():
        # Regla: se conserva el historial de ventas.
        motivo = (
            "Esta tienda tiene pedidos registrados y no se puede eliminar, para conservar el historial "
            "de ventas. Puedes desactivar la cuenta o suspender la tienda."
        )
    if motivo:
        messages.error(request, motivo)
        return redirect("administracion:usuarios")

    form = EliminarUsuarioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        nombre = str(usuario)
        try:
            with transaction.atomic():
                if tienda is not None:
                    for producto in tienda.productos.all():
                        producto.delete()  # así también se borran sus imágenes
                    borrar_archivo_al_confirmar(tienda.logo)
                usuario.delete()
        except ProtectedError:
            messages.error(request, "No se pudo eliminar: la cuenta tiene registros que deben conservarse.")
            return redirect("administracion:usuarios")
        messages.success(request, f"La cuenta \"{nombre}\" y sus datos fueron eliminados.")
        return redirect("administracion:usuarios")

    return render(request, "administracion/usuario_eliminar.html", {
        "usuario": usuario,
        "rol": rol_de(usuario),
        "tienda": tienda,
        "num_productos": tienda.productos.count() if tienda else 0,
        "num_favoritos": usuario.favoritos.count(),
        "form": form,
    })
