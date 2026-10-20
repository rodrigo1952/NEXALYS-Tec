from django import forms

from cuentas.estilos import EstiloBootstrapMixin

from .models import AccionAdmin


class MotivoForm(EstiloBootstrapMixin, forms.Form):
    """Motivo obligatorio para suspender, desactivar u ocultar (lo ve el afectado)."""

    motivo = forms.CharField(
        label="Motivo",
        min_length=5,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Ej.: Los precios publicados no coinciden con los de la tienda."}),
        help_text="La persona afectada verá este mensaje. Queda guardado en el historial.",
    )


class MotivoOpcionalForm(EstiloBootstrapMixin, forms.Form):
    """Para reactivar: el motivo es opcional, pero se guarda en el historial si se escribe."""

    motivo = forms.CharField(
        label="Motivo (opcional)",
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Ej.: La tienda corrigió sus precios."}),
        help_text="Queda guardado en el historial.",
    )


class EliminarUsuarioForm(EstiloBootstrapMixin, forms.Form):
    motivo = forms.CharField(
        label="Motivo",
        min_length=5,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Ej.: Cuenta duplicada a pedido del usuario."}),
        help_text="La cuenta desaparece, pero el motivo queda guardado en el historial.",
    )
    confirmar = forms.BooleanField(label="Entiendo que esta acción no se puede deshacer.")


class FiltroHistorialForm(forms.Form):
    tipo = forms.ChoiceField(choices=[("", "Todas las acciones"), *AccionAdmin.Tipo.choices], required=False)
    q = forms.CharField(required=False, max_length=100)
