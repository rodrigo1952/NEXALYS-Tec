from decimal import Decimal

from django import forms
from django.core.validators import RegexValidator

from catalogo.models import Producto
from catalogo.templatetags.formato import soles
from cuentas.estilos import EstiloBootstrapMixin

from .models import FichaInventario, Proveedor, Venta


class FichaForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = FichaInventario
        fields = ["costo", "stock_minimo", "codigo"]
        widgets = {
            "costo": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Ej.: 2300.00"}),
            "stock_minimo": forms.NumberInput(attrs={"min": "0"}),
        }

    def __init__(self, *args, tienda, **kwargs):
        super().__init__(*args, **kwargs)
        self.tienda = tienda
        self.fields["stock_minimo"].required = False

    def clean_stock_minimo(self):
        return self.cleaned_data.get("stock_minimo") or 0

    def clean_codigo(self):
        """Regla: el código interno no se repite dentro de la misma tienda (sin importar mayúsculas)."""
        codigo = (self.cleaned_data.get("codigo") or "").strip()
        if codigo:
            repetido = FichaInventario.objects.filter(producto__tienda=self.tienda, codigo__iexact=codigo)
            if self.instance.pk:
                repetido = repetido.exclude(pk=self.instance.pk)
            if repetido.exists():
                raise forms.ValidationError("Ya tienes otro producto con este código.")
        return codigo


class ProveedorForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ["nombre", "ruc", "telefono", "correo", "notas"]
        widgets = {
            "notas": forms.Textarea(attrs={"rows": 2, "placeholder": "Ej.: entrega los martes, pago contra entrega"}),
            "ruc": forms.TextInput(attrs={"inputmode": "numeric", "maxlength": "11"}),
        }

    def __init__(self, *args, tienda, **kwargs):
        super().__init__(*args, **kwargs)
        self.tienda = tienda
        self.instance.tienda = tienda

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split())
        repetido = Proveedor.objects.filter(tienda=self.tienda, nombre__iexact=nombre)
        if self.instance.pk:
            repetido = repetido.exclude(pk=self.instance.pk)
        if repetido.exists():
            raise forms.ValidationError("Ya tienes un proveedor con ese nombre.")
        return nombre


# ---------------------------------------------------------------------------
# Ventas
# ---------------------------------------------------------------------------

MAX_LINEAS_VENTA = 10


class SelectProducto(forms.Select):
    """Cada opción lleva el precio actual y el stock, para que la página sugiera el precio y calcule el total."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        opcion = super().create_option(name, value, label, selected, index, subindex, attrs)
        producto = getattr(value, "instance", None)
        if producto is not None:
            opcion["attrs"]["data-precio"] = str(producto.precio_final)
            opcion["attrs"]["data-stock"] = str(producto.stock)
        return opcion


class ProductoVentaField(forms.ModelChoiceField):
    def label_from_instance(self, producto):
        estado = "agotado" if producto.stock == 0 else f"stock {producto.stock}"
        return f"{producto.nombre} — {soles(producto.precio_final)} ({estado})"


class VentaForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Venta
        fields = ["metodo_pago", "cliente_nombre", "cliente_documento", "nota"]
        labels = {"cliente_nombre": "Cliente (opcional)", "cliente_documento": "DNI o RUC (opcional)", "nota": "Nota (opcional)"}
        widgets = {"cliente_documento": forms.TextInput(attrs={"inputmode": "numeric", "maxlength": "11"})}

    def clean_cliente_documento(self):
        documento = self.cleaned_data.get("cliente_documento", "").strip()
        if documento:
            RegexValidator(r"^(\d{8}|\d{11})$", "El DNI tiene 8 dígitos y el RUC 11.")(documento)
        return documento


class LineaVentaForm(EstiloBootstrapMixin, forms.Form):
    producto = ProductoVentaField(queryset=Producto.objects.none(), required=False, widget=SelectProducto,
                                  empty_label="Elige un producto")
    cantidad = forms.IntegerField(min_value=1, required=False, widget=forms.NumberInput(attrs={"min": "1"}))
    precio = forms.DecimalField(
        min_value=Decimal("0"), max_digits=10, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Precio actual"}),
        help_text="Vacío = precio publicado. Cámbialo si hiciste un descuento.",
    )

    def __init__(self, *args, tienda, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["producto"].queryset = Producto.objects.filter(tienda=tienda).order_by("nombre")

    def clean(self):
        datos = super().clean()
        producto, cantidad = datos.get("producto"), datos.get("cantidad")
        if producto and not cantidad:
            self.add_error("cantidad", "Indica la cantidad.")
        if cantidad and not producto:
            self.add_error("producto", "Elige el producto.")
        return datos


class BaseLineasVenta(forms.BaseFormSet):
    def clean(self):
        if any(self.errors):
            return
        if not any(f.cleaned_data.get("producto") for f in self.forms if f.cleaned_data):
            raise forms.ValidationError("Agrega al menos un producto a la venta.")


LineasVentaFormSet = forms.formset_factory(
    LineaVentaForm, formset=BaseLineasVenta, extra=MAX_LINEAS_VENTA, max_num=MAX_LINEAS_VENTA,
)


class AnularVentaForm(EstiloBootstrapMixin, forms.Form):
    motivo = forms.CharField(
        label="Motivo de la anulación", min_length=5, max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Ej.: Se registró dos veces por error"}),
    )
