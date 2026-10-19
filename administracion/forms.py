from django import forms

from cuentas.estilos import EstiloBootstrapMixin


class MotivoForm(EstiloBootstrapMixin, forms.Form):
    """Motivo para suspender una tienda u ocultar un producto (lo ve la tienda)."""

    motivo = forms.CharField(
        label="Motivo",
        min_length=5,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Ej.: Los precios publicados no coinciden con los de la tienda."}),
        help_text="La tienda verá este mensaje en su panel para saber qué corregir.",
    )


class EliminarUsuarioForm(EstiloBootstrapMixin, forms.Form):
    confirmar = forms.BooleanField(label="Entiendo que esta acción no se puede deshacer.")
