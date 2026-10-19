from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from cuentas.estilos import EstiloBootstrapMixin
from tiendas.models import Tienda

from .models import PRECIO_MINIMO, Categoria, Marca, Producto


class ProductoForm(EstiloBootstrapMixin, forms.ModelForm):
    """Formulario del CRUD de productos (CU-03). La tienda la asigna el sistema, no el usuario."""

    # Control de concurrencia (bloqueo optimista): guarda la fecha de la última
    # modificación del producto cuando se abrió el formulario. Si al guardar ya no
    # coincide (otra pestaña lo editó o un pedido cambió su stock), se avisa en vez
    # de sobrescribir los datos nuevos con los viejos.
    version = forms.CharField(widget=forms.HiddenInput, required=False)

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
        if self.instance.pk:
            self.fields["version"].initial = self.instance.actualizado.isoformat()

    def clean(self):
        datos = super().clean()
        version = datos.get("version")
        if self.instance.pk and version:
            actual = Producto.objects.filter(pk=self.instance.pk).first()
            if actual is None or actual.actualizado.isoformat() != version:
                # La próxima vez que guarde, ya sabiendo los datos actuales, se acepta.
                self.data = self.data.copy()
                self.data["version"] = actual.actualizado.isoformat() if actual else ""
                datos_actuales = (
                    f" Datos actuales: precio S/ {actual.precio}, stock {actual.stock}." if actual else ""
                )
                raise ValidationError(
                    "Este producto cambió mientras lo editabas (otra pestaña o un pedido modificó sus datos)."
                    f"{datos_actuales} Corrige lo que necesites y vuelve a guardar."
                )
        return datos

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


class NombreUnicoForm(EstiloBootstrapMixin, forms.ModelForm):
    """Base para categorías y marcas (CU-07): el nombre no se repite, sin importar mayúsculas."""

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split())
        if len(nombre) < 2:
            raise ValidationError("El nombre debe tener al menos 2 caracteres.")
        repetidos = self._meta.model.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            repetidos = repetidos.exclude(pk=self.instance.pk)
        if repetidos.exists():
            raise ValidationError("Ya existe un registro con ese nombre.")
        return nombre


class CategoriaForm(NombreUnicoForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "activa"]
        help_texts = {"activa": "Si la desactivas, las tiendas ya no podrán elegirla en productos nuevos."}


class MarcaForm(NombreUnicoForm):
    class Meta:
        model = Marca
        fields = ["nombre", "activa"]
        help_texts = {"activa": "Si la desactivas, las tiendas ya no podrán elegirla en productos nuevos."}
