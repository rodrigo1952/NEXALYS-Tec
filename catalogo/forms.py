from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from cuentas.estilos import EstiloBootstrapMixin
from tiendas.models import Tienda

from .models import PRECIO_MINIMO, Categoria, Marca, Producto


class ProductoForm(EstiloBootstrapMixin, forms.ModelForm):
    """Formulario del CRUD de productos (CU-03). La tienda la asigna el sistema, no el usuario."""

    class Meta:
        model = Producto
        fields = ["nombre", "categoria", "marca", "precio", "stock", "descripcion", "imagen", "activo"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 4}),
            "precio": forms.NumberInput(attrs={"step": "0.01", "min": str(PRECIO_MINIMO)}),
            "stock": forms.NumberInput(attrs={"min": "0"}),
        }

    def __init__(self, *args, tienda, **kwargs):
        super().__init__(*args, **kwargs)
        self.tienda = tienda
        self.instance.tienda = tienda
        # Solo se ofrecen categorías y marcas activas (más la que ya tenía el producto).
        self.fields["categoria"].queryset = Categoria.objects.filter(
            Q(activa=True) | Q(pk=self.instance.categoria_id)
        )
        self.fields["marca"].queryset = Marca.objects.filter(
            Q(activa=True) | Q(pk=self.instance.marca_id)
        )
        self.fields["categoria"].empty_label = "Selecciona una categoría"
        self.fields["marca"].empty_label = "Selecciona una marca"

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split())
        if len(nombre) < 3:
            raise ValidationError("El nombre debe tener al menos 3 caracteres.")
        # Regla de negocio: una tienda no puede tener dos productos con el mismo nombre.
        repetidos = Producto.objects.filter(tienda=self.tienda, nombre__iexact=nombre)
        if self.instance.pk:
            repetidos = repetidos.exclude(pk=self.instance.pk)
        if repetidos.exists():
            raise ValidationError("Ya tienes un producto registrado con ese nombre.")
        return nombre


class BusquedaForm(EstiloBootstrapMixin, forms.Form):
    """CU-04 Buscar y filtrar productos."""

    ORDENES = [
        ("recientes", "Más recientes"),
        ("precio_asc", "Precio: menor a mayor"),
        ("precio_desc", "Precio: mayor a menor"),
        ("nombre", "Nombre (A-Z)"),
    ]

    q = forms.CharField(label="Buscar", required=False, max_length=100)
    categoria = forms.ModelChoiceField(
        label="Categoría", queryset=Categoria.objects.filter(activa=True), required=False, empty_label="Todas"
    )
    marca = forms.ModelChoiceField(
        label="Marca", queryset=Marca.objects.filter(activa=True), required=False, empty_label="Todas"
    )
    tienda = forms.ModelChoiceField(
        label="Tienda",
        queryset=Tienda.objects.filter(estado=Tienda.Estado.ACTIVA),
        required=False,
        empty_label="Todas",
    )
    precio_min = forms.DecimalField(label="Precio mín.", required=False, min_value=0, decimal_places=2)
    precio_max = forms.DecimalField(label="Precio máx.", required=False, min_value=0, decimal_places=2)
    orden = forms.ChoiceField(label="Ordenar por", choices=ORDENES, required=False)

    def clean(self):
        datos = super().clean()
        minimo, maximo = datos.get("precio_min"), datos.get("precio_max")
        if minimo is not None and maximo is not None and minimo > maximo:
            raise ValidationError("El precio mínimo no puede ser mayor que el precio máximo.")
        return datos
