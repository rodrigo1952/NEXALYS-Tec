from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from catalogo.models import Producto
from cuentas.estilos import EstiloBootstrapMixin
from tiendas.forms import normalizar_whatsapp
from tiendas.models import validar_whatsapp

from .models import Pedido


class ProductoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, producto):
        oferta = " (oferta)" if producto.en_oferta else ""
        return f"{producto.nombre} — S/ {producto.precio_final}{oferta} (stock: {producto.stock})"


class PedidoForm(EstiloBootstrapMixin, forms.ModelForm):
    """Registrar o editar un pedido (CU-08). La tienda y el precio los asigna el sistema."""

    producto = ProductoChoiceField(queryset=Producto.objects.none(), label="Producto", empty_label="Selecciona un producto")

    class Meta:
        model = Pedido
        fields = ["producto", "cantidad", "cliente_nombre", "cliente_telefono", "observacion"]
        widgets = {
            "cantidad": forms.NumberInput(attrs={"min": "1"}),
            "observacion": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, tienda, **kwargs):
        super().__init__(*args, **kwargs)
        self.tienda = tienda
        self.instance.tienda = tienda
        # Regla: solo productos de la propia tienda con stock (más el que ya tenía el pedido).
        self.fields["producto"].queryset = Producto.objects.filter(tienda=tienda).filter(
            Q(stock__gt=0) | Q(pk=self.instance.producto_id)
        )

    def clean_cliente_nombre(self):
        nombre = " ".join(self.cleaned_data["cliente_nombre"].split())
        if len(nombre) < 3:
            raise ValidationError("Ingresa el nombre completo del cliente.")
        return nombre

    def clean_cliente_telefono(self):
        numero = normalizar_whatsapp(self.cleaned_data["cliente_telefono"])
        validar_whatsapp(numero)
        return numero

    def clean(self):
        datos = super().clean()
        producto, cantidad = datos.get("producto"), datos.get("cantidad")
        if producto and cantidad:
            disponible = producto.stock
            # Al editar, las unidades que ya reservó este pedido vuelven a estar disponibles.
            if self.instance.pk and self.instance.producto_id == producto.pk:
                disponible += Pedido.objects.get(pk=self.instance.pk).cantidad
            if cantidad > disponible:
                self.add_error("cantidad", f"Stock insuficiente: solo hay {disponible} unidad(es) disponibles.")
        return datos


class FiltroPedidosForm(EstiloBootstrapMixin, forms.Form):
    q = forms.CharField(label="Cliente", required=False, max_length=100)
    estado = forms.ChoiceField(
        label="Estado",
        required=False,
        choices=[("", "Todos")] + list(Pedido.Estado.choices),
    )
