"""
Panel de administración con el diseño de NEXALYS (rol Administrador).

Reemplaza el uso diario de Django Admin: resumen, tiendas, productos, ventas y
usuarios. Categorías y marcas siguen en catalogo/gestion.py. Django Admin queda
como herramienta avanzada.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, DecimalField, OuterRef, ProtectedError, Q, Subquery, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from catalogo.models import Categoria, Marca, Producto, borrar_archivo_al_confirmar
from cuentas.views import rol_requerido
from inventario.models import Venta
from tiendas.models import DIAS_PARA_ELIMINAR_SUSPENDIDA, Tienda

from . import acciones, limpieza
from .forms import EliminarUsuarioForm, FiltroHistorialForm, MotivoForm, MotivoOpcionalForm
from .models import AccionAdmin

solo_admin = rol_requerido("Administrador")

MESES_VENTAS = 6  # columnas de la tabla de ventas por tienda
NOMBRES_MES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"]


def _ventas_validas():
    """Privacidad: el administrador solo ve TOTALES de ventas (nunca costos, ganancias ni clientes)."""
    return Venta.objects.filter(anulada=False)


def _inicio_mes_actual():
    return timezone.make_aware(datetime.combine(timezone.localdate().replace(day=1), time.min))


def _entero(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _datos(request):
    """
    Datos del formulario solo si se envió (POST). Ojo: "request.POST or None" falla cuando
    el POST llega vacío (p. ej. reactivar sin escribir motivo): un POST vacío es "falso"
    y el formulario se trataría como no enviado.
    """
    return request.POST if request.method == "POST" else None


def _confirmar(request, *, titulo, color, consecuencias, form, boton, cancelar, aviso=""):
    """
    Paso 2 de toda acción delicada: página que resume lo que va a pasar y pide el motivo.
    El paso 1 es el botón (un enlace) que trae hasta aquí; la acción se hace al enviar este formulario.
    """
    return render(request, "administracion/confirmar.html", {
        "titulo": titulo, "color": color, "consecuencias": consecuencias, "form": form,
        "boton": boton, "cancelar": cancelar, "aviso": aviso,
    }, status=400 if request.method == "POST" else 200)


def _volver(request, por_defecto):
    """Regresa a la página anterior (solo si es de este sitio)."""
    destino = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return redirect(destino)
    return redirect(por_defecto)


# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------

def _limpiar(request):
    """Elimina las tiendas suspendidas hace 90 días y las cuentas sin confirmar hace 7 (ver limpieza.py)."""
    tiendas, cuentas = limpieza.ejecutar()
    if tiendas:
        messages.info(
            request,
            f"Se eliminaron automáticamente {tiendas} tienda(s) que estuvieron suspendidas más de 90 días. "
            "Quedó registrado en el Historial.",
        )
    if cuentas:
        messages.info(request, f"Se eliminaron {cuentas} cuenta(s) de cliente que no confirmaron su correo en 7 días.")


@solo_admin
def resumen(request):
    _limpiar(request)
    estados = dict(Tienda.objects.order_by().values_list("estado").annotate(n=Count("id")))
    ventas_mes = _ventas_validas().filter(fecha__gte=_inicio_mes_actual())
    return render(request, "cuentas/panel_admin.html", {
        "tiendas_activas": estados.get(Tienda.Estado.ACTIVA, 0),
        "tiendas_pendientes": estados.get(Tienda.Estado.PENDIENTE, 0),
        "tiendas_suspendidas": estados.get(Tienda.Estado.SUSPENDIDA, 0),
        "productos_publicados": Producto.objects.visibles().count(),
        "productos_ocultos": Producto.objects.filter(oculto_por_admin=True).count(),
        "clientes": User.objects.filter(groups__name="Cliente").count(),
        "ventas_mes": ventas_mes.aggregate(t=Sum("total"))["t"] or 0,
        "tiendas_con_ventas": ventas_mes.exclude(tienda=None).values("tienda").distinct().count(),
        "categorias": Categoria.objects.count(),
        "marcas": Marca.objects.count(),
        "por_eliminarse": limpieza.por_eliminarse_pronto()[:10],
    })


# ---------------------------------------------------------------------------
# Tiendas
# ---------------------------------------------------------------------------

@solo_admin
def tiendas(request):
    _limpiar(request)
    lista = Tienda.objects.select_related("usuario").annotate(
        num_productos=Count("productos", distinct=True),
    ).annotate(
        vendido_mes=Subquery(
            _ventas_validas().filter(tienda=OuterRef("pk"), fecha__gte=_inicio_mes_actual())
            .order_by().values("tienda").annotate(t=Sum("total")).values("t")[:1],
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    ).order_by("nombre")
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
        "total_productos": productos.count(),
        "publicados": productos.filter(activo=True, oculto_por_admin=False).count(),
        "ocultos_admin": productos.filter(oculto_por_admin=True).count(),
        "vendido_mes": _ventas_validas().filter(tienda=tienda, fecha__gte=_inicio_mes_actual())
        .aggregate(t=Sum("total"))["t"] or 0,
    })


@solo_admin
def tienda_suspender(request, pk):
    tienda = get_object_or_404(Tienda.objects.select_related("usuario"), pk=pk)
    detalle = reverse("administracion:tienda_detalle", args=[tienda.pk])
    if tienda.estado == Tienda.Estado.SUSPENDIDA:
        messages.info(request, f"La tienda \"{tienda}\" ya está suspendida.")
        return redirect(detalle)
    form = MotivoForm(_datos(request))
    if request.method == "POST" and form.is_valid():
        if acciones.suspender_tienda(request.user, tienda, form.cleaned_data["motivo"]):
            messages.warning(request, f"La tienda \"{tienda}\" fue suspendida; sus productos ya no se ven en el catálogo.")
        else:
            messages.info(request, f"La tienda \"{tienda}\" ya había sido suspendida.")
        return redirect(detalle)
    publicados = tienda.productos.filter(activo=True, oculto_por_admin=False).count()
    return _confirmar(
        request,
        titulo=f"Suspender la tienda «{tienda.nombre}»",
        color="danger",
        consecuencias=[
            f"{publicados} producto{'s' if publicados != 1 else ''} publicado{'s' if publicados != 1 else ''} dejará{'n' if publicados != 1 else ''} de verse en el catálogo, en Inicio y en los favoritos de los clientes.",
            "Su perfil público dejará de mostrarse.",
            "La tienda podrá iniciar sesión y verá el motivo en su panel.",
            f"Si no la reactivas en {DIAS_PARA_ELIMINAR_SUSPENDIDA} días, se eliminará automáticamente "
            "(cuenta, productos e imágenes); sus ventas se conservan anónimas.",
        ],
        form=form,
        boton="Suspender tienda",
        cancelar=detalle,
    )


@solo_admin
def tienda_reactivar(request, pk):
    tienda = get_object_or_404(Tienda.objects.select_related("usuario"), pk=pk)
    detalle = reverse("administracion:tienda_detalle", args=[tienda.pk])
    if tienda.estado != Tienda.Estado.SUSPENDIDA:
        messages.info(request, f"La tienda \"{tienda}\" no está suspendida.")
        return redirect(detalle)
    form = MotivoOpcionalForm(_datos(request))
    if request.method == "POST" and form.is_valid():
        tienda = acciones.reactivar_tienda(request.user, tienda, form.cleaned_data["motivo"])
        if tienda is None:
            messages.info(request, "La tienda ya había sido reactivada.")
        elif tienda.estado == Tienda.Estado.ACTIVA:
            messages.success(request, f"La tienda \"{tienda}\" fue reactivada.")
        else:
            messages.info(request, f"\"{tienda}\" quedó pendiente: aún debe verificar su correo para activarse.")
        return redirect(detalle)
    consecuencias = [
        "Sus productos publicados vuelven a verse en el catálogo." if tienda.verificada_en
        else "Como aún no verificó su correo, quedará PENDIENTE hasta que lo haga.",
        "Se borra el motivo de la suspensión de su panel.",
    ]
    if not tienda.usuario.is_active:
        consecuencias.append(f"Su cuenta «{tienda.usuario.username}» también se reactiva y podrá iniciar sesión.")
    return _confirmar(
        request,
        titulo=f"Reactivar la tienda «{tienda.nombre}»",
        color="success",
        consecuencias=consecuencias,
        form=form,
        boton="Reactivar tienda",
        cancelar=detalle,
        aviso=f"Motivo de la suspensión: {tienda.motivo_suspension or '(sin motivo registrado)'}",
    )


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
    form = MotivoForm(_datos(request))
    if request.method == "POST" and form.is_valid():
        producto.oculto_por_admin = True
        producto.motivo_ocultamiento = form.cleaned_data["motivo"].strip()
        producto.save(update_fields=["oculto_por_admin", "motivo_ocultamiento", "actualizado"])
        acciones.registrar(
            request.user, AccionAdmin.Tipo.OCULTAR_PRODUCTO,
            f"Producto «{producto.nombre}» de {producto.tienda}", producto.motivo_ocultamiento, producto.tienda.usuario,
        )
        messages.warning(request, f"\"{producto}\" ya no se ve en el catálogo. La tienda verá el motivo.")
        return redirect("administracion:productos")
    return render(request, "administracion/producto_ocultar.html", {"producto": producto, "form": form})


@require_POST
@solo_admin
def producto_mostrar(request, pk):
    producto = get_object_or_404(Producto.objects.select_related("tienda"), pk=pk)
    producto.oculto_por_admin = False
    producto.motivo_ocultamiento = ""
    producto.save(update_fields=["oculto_por_admin", "motivo_ocultamiento", "actualizado"])
    acciones.registrar(
        request.user, AccionAdmin.Tipo.MOSTRAR_PRODUCTO,
        f"Producto «{producto.nombre}» de {producto.tienda}", usuario=producto.tienda.usuario,
    )
    messages.success(request, f"\"{producto}\" vuelve a mostrarse (si la tienda lo tiene publicado).")
    return _volver(request, "administracion:productos")


# ---------------------------------------------------------------------------
# Ventas (solo totales por tienda y mes)
# ---------------------------------------------------------------------------

def _meses_atras(cantidad):
    """Primer día de los últimos `cantidad` meses, del más antiguo al actual."""
    actual = timezone.localdate().replace(day=1)
    meses = [actual]
    for _ in range(cantidad - 1):
        meses.insert(0, (meses[0] - timedelta(days=1)).replace(day=1))
    return meses


@solo_admin
def ventas(request):
    """
    Tabla de ventas: filas = tiendas, columnas = últimos 6 meses y total.
    Solo totales vendidos (sin anuladas). Las tiendas eliminadas se agrupan como "Tienda eliminada".
    """
    meses = _meses_atras(MESES_VENTAS)
    desde = timezone.make_aware(datetime.combine(meses[0], time.min))
    filas_bd = (
        _ventas_validas().filter(fecha__gte=desde)
        .annotate(mes=TruncMonth("fecha")).order_by()
        .values("tienda_id", "mes").annotate(total=Sum("total"))
    )
    por_tienda = {}
    for fila in filas_bd:
        mes = fila["mes"]
        mes = (timezone.localtime(mes) if timezone.is_aware(mes) else mes).date().replace(day=1)
        por_tienda.setdefault(fila["tienda_id"], {})[mes] = fila["total"]

    filas = []
    for tienda in Tienda.objects.order_by("nombre"):
        montos = [por_tienda.get(tienda.pk, {}).get(m, Decimal("0")) for m in meses]
        filas.append({"tienda": tienda, "nombre": tienda.nombre, "montos": montos, "total": sum(montos)})
    if None in por_tienda:
        montos = [por_tienda[None].get(m, Decimal("0")) for m in meses]
        filas.append({"tienda": None, "nombre": limpieza.NOMBRE_ANONIMO, "montos": montos, "total": sum(montos)})
    filas.sort(key=lambda f: (-f["total"], f["nombre"].lower()))
    totales = [sum(f["montos"][i] for f in filas) for i in range(len(meses))]
    return render(request, "administracion/ventas.html", {
        "meses": [f"{NOMBRES_MES[m.month - 1]} {m:%Y}" for m in meses],
        "filas": filas, "totales": totales, "total_general": sum(totales),
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
    lista = (
        User.objects.select_related("tienda", "correo_pendiente").prefetch_related("groups").order_by("-date_joined")
    )
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
        usuario.sin_confirmar = hasattr(usuario, "correo_pendiente")
        usuario.protegido = _motivo_no_se_puede_modificar(request.user, usuario) is not None
    return render(request, "administracion/usuarios.html", {
        "pagina": pagina, "q": texto, "rol": rol, "estado": estado,
    })


def _usuario_modificable(request, pk):
    """Devuelve (usuario, None) o (None, respuesta de error) según las reglas de protección."""
    usuario = get_object_or_404(User.objects.select_related("tienda"), pk=pk)
    motivo = _motivo_no_se_puede_modificar(request.user, usuario)
    if motivo:
        messages.error(request, motivo)
        return None, redirect("administracion:usuarios")
    return usuario, None


@solo_admin
def usuario_desactivar(request, pk):
    """Desactiva una cuenta: no puede iniciar sesión. Si es una tienda, también se suspende."""
    usuario, error = _usuario_modificable(request, pk)
    if error:
        return error
    lista = reverse("administracion:usuarios")
    if not usuario.is_active:
        messages.info(request, f"La cuenta \"{usuario}\" ya está desactivada.")
        return redirect(lista)
    tienda = getattr(usuario, "tienda", None)
    form = MotivoForm(_datos(request))
    if request.method == "POST" and form.is_valid():
        if acciones.desactivar_cuenta(request.user, usuario, form.cleaned_data["motivo"]):
            texto = f"La cuenta \"{usuario}\" fue desactivada: ya no puede iniciar sesión."
            if tienda is not None:
                texto += f" La tienda \"{tienda}\" también fue suspendida y sus productos ya no se ven."
            messages.warning(request, texto)
        else:
            messages.info(request, f"La cuenta \"{usuario}\" ya había sido desactivada.")
        return redirect(lista)
    consecuencias = [
        "No podrá iniciar sesión. Al intentarlo verá el motivo que escribas.",
        "Sus datos se conservan y la puedes reactivar cuando quieras.",
    ]
    if tienda is not None:
        publicados = tienda.productos.filter(activo=True, oculto_por_admin=False).count()
        if tienda.estado == Tienda.Estado.SUSPENDIDA:
            consecuencias.append(f"Su tienda «{tienda.nombre}» ya está suspendida y seguirá así.")
        else:
            consecuencias.append(
                f"Su tienda «{tienda.nombre}» también se suspende: {publicados} producto{'s' if publicados != 1 else ''} "
                f"dejará{'n' if publicados != 1 else ''} de verse y su perfil público se oculta."
            )
    return _confirmar(
        request,
        titulo=f"Desactivar la cuenta «{usuario.username}»",
        color="warning",
        consecuencias=consecuencias,
        form=form,
        boton="Desactivar cuenta",
        cancelar=lista,
    )


@solo_admin
def usuario_reactivar(request, pk):
    usuario, error = _usuario_modificable(request, pk)
    if error:
        return error
    lista = reverse("administracion:usuarios")
    if usuario.is_active:
        messages.info(request, f"La cuenta \"{usuario}\" ya está activa.")
        return redirect(lista)
    tienda = getattr(usuario, "tienda", None)
    form = MotivoOpcionalForm(_datos(request))
    if request.method == "POST" and form.is_valid():
        if acciones.reactivar_cuenta(request.user, usuario, form.cleaned_data["motivo"]):
            messages.success(request, f"La cuenta \"{usuario}\" fue reactivada.")
        else:
            messages.info(request, f"La cuenta \"{usuario}\" ya había sido reactivada.")
        return redirect(lista)
    consecuencias = ["Podrá volver a iniciar sesión."]
    if tienda is not None and tienda.estado == Tienda.Estado.SUSPENDIDA:
        consecuencias.append(
            f"Su tienda «{tienda.nombre}» también se reactiva"
            + (" y sus productos vuelven a verse." if tienda.verificada_en else " (quedará pendiente hasta que verifique su correo).")
        )
    motivo_anterior = acciones.motivo_desactivacion(usuario)
    return _confirmar(
        request,
        titulo=f"Reactivar la cuenta «{usuario.username}»",
        color="success",
        consecuencias=consecuencias,
        form=form,
        boton="Reactivar cuenta",
        cancelar=lista,
        aviso=f"Motivo de la desactivación: {motivo_anterior}" if motivo_anterior else "",
    )


@solo_admin
def usuario_eliminar(request, pk):
    usuario = get_object_or_404(User.objects.select_related("tienda"), pk=pk)
    motivo = _motivo_no_se_puede_modificar(request.user, usuario)
    tienda = getattr(usuario, "tienda", None)
    if not motivo and tienda is not None and tienda.ventas.exists():
        # Regla: se conserva el historial de ventas.
        motivo = (
            "Esta tienda tiene ventas registradas y no se puede eliminar, para conservar el historial "
            "de ventas. Puedes desactivar la cuenta o suspender la tienda."
        )
    if motivo:
        messages.error(request, motivo)
        return redirect("administracion:usuarios")

    form = EliminarUsuarioForm(_datos(request))
    if request.method == "POST" and form.is_valid():
        nombre = str(usuario)
        objetivo = f"{acciones.texto_cuenta(usuario)} ({rol_de(usuario)}{', tienda «' + tienda.nombre + '»' if tienda else ''})"
        try:
            with transaction.atomic():
                # Se registra primero: si algo falla, la transacción deshace también el registro.
                acciones.registrar(request.user, AccionAdmin.Tipo.ELIMINAR_CUENTA, objetivo, form.cleaned_data["motivo"])
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


# ---------------------------------------------------------------------------
# Historial de acciones del administrador
# ---------------------------------------------------------------------------

@solo_admin
def historial(request):
    form = FiltroHistorialForm(request.GET or None)
    lista = AccionAdmin.objects.all()
    tipo = texto = ""
    if form.is_valid():
        tipo = form.cleaned_data["tipo"]
        texto = form.cleaned_data["q"].strip()
        if tipo:
            lista = lista.filter(tipo=tipo)
        if texto:
            lista = lista.filter(
                Q(objetivo__icontains=texto) | Q(motivo__icontains=texto) | Q(admin_nombre__icontains=texto)
            )
    pagina = Paginator(lista, 25).get_page(request.GET.get("page"))
    return render(request, "administracion/historial.html", {
        "pagina": pagina, "tipo": tipo, "q": texto, "tipos": AccionAdmin.Tipo.choices,
    })
