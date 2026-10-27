import unicodedata
from decimal import Decimal

from django import forms
from django.core.validators import RegexValidator
from django.db.models import F

from catalogo.models import Producto
from catalogo.templatetags.formato import soles
from cuentas.estilos import EstiloBootstrapMixin

from .models import Ingreso, Movimiento, Proveedor, Venta


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


def sin_tildes(texto):
    """'Cámara Logitech' -> 'camara logitech' (para buscar sin importar tildes ni mayúsculas)."""
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def productos_para_elegir(tienda):
    """Productos de la tienda con lo que necesita el buscador (código, marca, categoría y costo)."""
    return (
        Producto.objects.filter(tienda=tienda)
        .select_related("marca", "categoria")
        .annotate(costo_ficha=F("ficha__costo"), codigo_ficha=F("ficha__codigo"))
        .order_by("nombre")
    )


class SelectProducto(forms.Select):
    """
    Lista de productos con buscador (static/js/buscador_productos.js).

    Cada opción lleva el precio actual, el stock y (si se conoce) el costo, para que la
    página sugiera el precio o el costo y calcule el total; y el texto en el que se
    busca: nombre, código, marca y categoría, sin tildes.
    """

    def __init__(self, attrs=None, choices=()):
        super().__init__({"class": "buscador-producto", **(attrs or {})}, choices)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        opcion = super().create_option(name, value, label, selected, index, subindex, attrs)
        producto = getattr(value, "instance", None)
        if producto is not None:
            opcion["attrs"]["data-precio"] = str(producto.precio_final)
            opcion["attrs"]["data-stock"] = str(producto.stock)
            costo = getattr(producto, "costo_ficha", None)
            if costo is not None:
                opcion["attrs"]["data-costo"] = str(costo)
            codigo = getattr(producto, "codigo_ficha", "") or ""
            if codigo:
                opcion["attrs"]["data-codigo"] = sin_tildes(codigo)
            partes = [producto.nombre, codigo, producto.marca.nombre, producto.categoria.nombre]
            opcion["attrs"]["data-buscar"] = sin_tildes(" ".join(p for p in partes if p))
        return opcion


def _codigo_y_stock(producto):
    codigo = getattr(producto, "codigo_ficha", "") or ""
    stock = "agotado" if producto.stock == 0 else f"stock {producto.stock}"
    return (f"Cód. {codigo} · " if codigo else "") + stock


class ProductoVentaField(forms.ModelChoiceField):
    def label_from_instance(self, producto):
        return f"{producto.nombre} · {soles(producto.precio_final)} · {_codigo_y_stock(producto)}"


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
        self.fields["producto"].queryset = productos_para_elegir(tienda)

    def clean(self):
        datos = super().clean()
        producto, cantidad = datos.get("producto"), datos.get("cantidad")
        if producto and not cantidad:
            self.add_error("cantidad", "Indica la cantidad.")
        if cantidad and not producto:
            self.add_error("producto", "Elige el producto.")
        return datos


class BaseLineas(forms.BaseFormSet):
    mensaje_vacio = "Agrega al menos un producto."

    def clean(self):
        if any(self.errors):
            return
        if not any(f.cleaned_data.get("producto") for f in self.forms if f.cleaned_data):
            raise forms.ValidationError(self.mensaje_vacio)


class BaseLineasVenta(BaseLineas):
    mensaje_vacio = "Agrega al menos un producto a la venta."


LineasVentaFormSet = forms.formset_factory(
    LineaVentaForm, formset=BaseLineasVenta, extra=MAX_LINEAS_VENTA, max_num=MAX_LINEAS_VENTA,
)


class AnularVentaForm(EstiloBootstrapMixin, forms.Form):
    motivo = forms.CharField(
        label="Motivo de la anulación", min_length=5, max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Ej.: Se registró dos veces por error"}),
    )


# ---------------------------------------------------------------------------
# Ingresos de mercadería (Etapa 3)
# ---------------------------------------------------------------------------

class ProductoIngresoField(forms.ModelChoiceField):
    def label_from_instance(self, producto):
        return f"{producto.nombre} · {_codigo_y_stock(producto)}"


class IngresoForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Ingreso
        fields = ["proveedor", "documento", "nota"]
        labels = {"proveedor": "Proveedor (opcional)", "documento": "N.° de factura o guía (opcional)",
                  "nota": "Nota (opcional)"}
        widgets = {"documento": forms.TextInput(attrs={"placeholder": "Ej.: F001-000123"})}

    def __init__(self, *args, tienda, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["proveedor"].queryset = Proveedor.objects.filter(tienda=tienda)
        self.fields["proveedor"].empty_label = "Sin proveedor"


class LineaIngresoForm(EstiloBootstrapMixin, forms.Form):
    producto = ProductoIngresoField(queryset=Producto.objects.none(), required=False, widget=SelectProducto,
                                    empty_label="Elige un producto")
    cantidad = forms.IntegerField(min_value=1, required=False, widget=forms.NumberInput(attrs={"min": "1"}))
    costo = forms.DecimalField(
        min_value=Decimal("0"), max_digits=10, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Costo unitario"}),
    )

    def __init__(self, *args, tienda, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["producto"].queryset = productos_para_elegir(tienda)

    def clean(self):
        datos = super().clean()
        producto, cantidad, costo = datos.get("producto"), datos.get("cantidad"), datos.get("costo")
        if producto:
            if not cantidad and "cantidad" not in self.errors:
                self.add_error("cantidad", "Indica la cantidad.")
            if costo is None and "costo" not in self.errors:
                self.add_error("costo", "Indica cuánto pagaste por unidad.")
        elif cantidad or costo is not None:
            self.add_error("producto", "Elige el producto.")
        return datos


class BaseLineasIngreso(BaseLineas):
    mensaje_vacio = "Agrega al menos un producto al ingreso."


LineasIngresoFormSet = forms.formset_factory(
    LineaIngresoForm, formset=BaseLineasIngreso, extra=MAX_LINEAS_VENTA, max_num=MAX_LINEAS_VENTA,
)


class AnularIngresoForm(AnularVentaForm):
    pass


# ---------------------------------------------------------------------------
# Ajustes (Etapa 3)
# ---------------------------------------------------------------------------

M = Movimiento.Motivo


class AjusteForm(EstiloBootstrapMixin, forms.Form):
    # Cada opción dice si suma o resta, para que no haya dudas.
    OPCIONES = [
        (M.DANO, "Producto dañado (resta)"),
        (M.PERDIDA, "Pérdida o robo (resta)"),
        (M.DEVOLUCION_CLIENTE, "Devolución de un cliente (suma)"),
        (M.DEVOLUCION_PROVEEDOR, "Devolución al proveedor (resta)"),
        ("otro_suma", "Otro motivo (suma)"),
        ("otro_resta", "Otro motivo (resta)"),
    ]
    QUE_SUMAN = {M.DEVOLUCION_CLIENTE.value, "otro_suma"}

    producto = ProductoIngresoField(queryset=Producto.objects.none(), widget=SelectProducto,
                                    empty_label="Elige un producto")
    motivo = forms.ChoiceField(label="Motivo", choices=[("", "Elige el motivo")] + OPCIONES)
    cantidad = forms.IntegerField(label="Cantidad", min_value=1, widget=forms.NumberInput(attrs={"min": "1"}))
    nota = forms.CharField(
        label="Detalle", max_length=200, required=False,
        widget=forms.TextInput(attrs={"placeholder": "Ej.: Pantalla rota al desempacar"}),
        help_text="Obligatorio si eliges «Otro motivo».",
    )

    def __init__(self, *args, tienda, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["producto"].queryset = productos_para_elegir(tienda)

    def clean(self):
        datos = super().clean()
        motivo = datos.get("motivo", "")
        if motivo.startswith("otro") and not datos.get("nota", "").strip():
            self.add_error("nota", "Explica el motivo del ajuste.")
        return datos

    def motivo_y_cantidad(self):
        """Devuelve el motivo que se guarda y la cantidad con signo (+ suma, − resta)."""
        motivo, cantidad = self.cleaned_data["motivo"], self.cleaned_data["cantidad"]
        signo = 1 if motivo in self.QUE_SUMAN else -1
        return (M.OTRO.value if motivo.startswith("otro") else motivo), signo * cantidad
