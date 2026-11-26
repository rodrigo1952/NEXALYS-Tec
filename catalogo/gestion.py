"""
CU-07 Gestionar categorías y marcas.
CRUD dentro de la aplicación, solo para el rol Administrador.
Las dos entidades funcionan igual, así que comparten las mismas vistas y plantillas.

Eliminar (nov 2026): si la categoría o marca todavía tiene productos, el administrador elige a cuál
pasan (por defecto «Otros») y luego se elimina. Queda anotado en el Historial.
"""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from administracion import acciones
from administracion.models import AccionAdmin
from cuentas.views import rol_requerido

from .forms import CategoriaForm, MarcaForm, MoverProductosForm
from .models import Categoria, Marca, Producto

TIPOS = {
    "categorias": {
        "modelo": Categoria, "form": CategoriaForm, "singular": "categoría", "plural": "Categorías",
        "campo": "categoria", "accion": AccionAdmin.Tipo.ELIMINAR_CATEGORIA,
    },
    "marcas": {
        "modelo": Marca, "form": MarcaForm, "singular": "marca", "plural": "Marcas",
        "campo": "marca", "accion": AccionAdmin.Tipo.ELIMINAR_MARCA,
    },
}


def _config(tipo):
    if tipo not in TIPOS:
        raise Http404("Tipo no válido")
    return {"tipo": tipo, **TIPOS[tipo]}


@rol_requerido("Administrador")
def gestion_lista(request, tipo):
    config = _config(tipo)
    registros = config["modelo"].objects.annotate(num_productos=Count("productos")).order_by("nombre")
    texto = request.GET.get("q", "").strip()
    if texto:
        registros = registros.filter(nombre__icontains=texto)
    pagina = Paginator(registros, 15).get_page(request.GET.get("page"))
    return render(request, "catalogo/gestion_lista.html", {**config, "pagina": pagina, "q": texto})


@rol_requerido("Administrador")
def gestion_crear(request, tipo):
    config = _config(tipo)
    form = config["form"](request.POST or None)
    if request.method == "POST" and form.is_valid():
        registro = form.save()
        messages.success(request, f"{config['singular'].capitalize()} \"{registro}\" registrada correctamente.")
        return redirect("catalogo:gestion_lista", tipo=tipo)
    titulo = f"Nueva {config['singular']}"
    return render(request, "catalogo/gestion_form.html", {**config, "form": form, "titulo": titulo})


@rol_requerido("Administrador")
def gestion_editar(request, tipo, pk):
    config = _config(tipo)
    registro = get_object_or_404(config["modelo"], pk=pk)
    form = config["form"](request.POST or None, instance=registro)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{config['singular'].capitalize()} \"{registro}\" actualizada.")
        return redirect("catalogo:gestion_lista", tipo=tipo)
    titulo = f"Editar {config['singular']}"
    return render(request, "catalogo/gestion_form.html", {**config, "form": form, "titulo": titulo})


def _mover_productos(campo, registro, destino):
    """Pasa todos los productos de `registro` a `destino` y recalcula su texto de búsqueda. Devuelve cuántos."""
    ids = list(Producto.objects.select_for_update().filter(**{campo: registro}).values_list("pk", flat=True))
    if ids:
        Producto.objects.filter(pk__in=ids).update(**{campo: destino})
        Producto.actualizar_texto_busqueda(Producto.objects.filter(pk__in=ids))
    return len(ids)


@rol_requerido("Administrador")
def gestion_eliminar(request, tipo, pk):
    config = _config(tipo)
    modelo, campo, singular = config["modelo"], config["campo"], config["singular"]
    registro = get_object_or_404(modelo, pk=pk)
    productos = registro.productos.all()
    num_productos = productos.count()
    num_tiendas = productos.values("tienda").distinct().count()
    # Regla de negocio: ningún producto se queda sin categoría o marca. Si tiene productos,
    # primero pasan a otra (activa) y después se elimina.
    datos = request.POST if request.method == "POST" else None
    form = MoverProductosForm(modelo, registro, singular, datos) if num_productos else None
    if datos is not None and (form is None or form.is_valid()):
        destino = form.cleaned_data["destino"] if form else None
        nombre = str(registro)
        try:
            with transaction.atomic():
                movidos = _mover_productos(campo, registro, destino) if destino else 0
                registro.delete()
                motivo = (f"Sus {movidos} producto(s) pasaron a la {singular} «{destino}»." if movidos
                          else "No tenía productos.")
                acciones.registrar(request.user, config["accion"], f"{singular.capitalize()} «{nombre}»", motivo)
        except ProtectedError:
            # Una tienda le asignó un producto justo ahora (sin elegir destino): se vuelve a mostrar la página.
            messages.error(request, f"No se eliminó «{nombre}»: acaba de recibir productos. Revisa y vuelve a intentarlo.")
            return redirect("catalogo:gestion_eliminar", tipo=tipo, pk=pk)
        aviso = f"{singular.capitalize()} «{nombre}» eliminada."
        if movidos:
            aviso += f" Sus {movidos} producto(s) pasaron a «{destino}»."
        messages.success(request, aviso)
        return redirect("catalogo:gestion_lista", tipo=tipo)
    return render(
        request,
        "catalogo/gestion_confirmar_eliminar.html",
        {**config, "registro": registro, "num_productos": num_productos, "num_tiendas": num_tiendas, "form": form},
    )
