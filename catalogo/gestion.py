"""
CU-07 Gestionar categorías y marcas.
CRUD dentro de la aplicación, solo para el rol Administrador.
Las dos entidades funcionan igual, así que comparten las mismas vistas y plantillas.
"""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from cuentas.views import rol_requerido

from .forms import CategoriaForm, MarcaForm
from .models import Categoria, Marca

TIPOS = {
    "categorias": {"modelo": Categoria, "form": CategoriaForm, "singular": "categoría", "plural": "Categorías"},
    "marcas": {"modelo": Marca, "form": MarcaForm, "singular": "marca", "plural": "Marcas"},
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


@rol_requerido("Administrador")
def gestion_eliminar(request, tipo, pk):
    config = _config(tipo)
    registro = get_object_or_404(config["modelo"], pk=pk)
    num_productos = registro.productos.count()
    # Regla de negocio: no se elimina una categoría o marca que tiene productos;
    # en su lugar se desactiva, para no dejar productos sin clasificar.
    if request.method == "POST":
        if num_productos:
            messages.error(
                request,
                f"No se puede eliminar \"{registro}\": tiene {num_productos} producto(s). Desactívala en su lugar.",
            )
        else:
            nombre = str(registro)
            registro.delete()
            messages.success(request, f"{config['singular'].capitalize()} \"{nombre}\" eliminada.")
        return redirect("catalogo:gestion_lista", tipo=tipo)
    return render(
        request,
        "catalogo/gestion_confirmar_eliminar.html",
        {**config, "registro": registro, "num_productos": num_productos},
    )
