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


class RestablecerClaveForm(EstiloBootstrapMixin, forms.Form):
    """Motivo para dar una clave temporal (queda en el historial)."""

    MOTIVOS = (
        ("olvido", "Olvidó su contraseña"),
        ("correo", "No le llega el correo de recuperación"),
        ("robada", "Cuenta posiblemente robada"),
        ("otro", "Otro motivo"),
    )
    motivo = forms.ChoiceField(label="Motivo", choices=MOTIVOS, widget=forms.RadioSelect)
    detalle = forms.CharField(
        label="Detalle",
        required=False,
        max_length=300,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Ej.: Llamó a la tienda y confirmó su DNI y su correo."}),
        help_text="Obligatorio si eliges «Otro motivo». Queda guardado en el historial.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["motivo"].widget.attrs["class"] = "form-check-input"
        self.fields["motivo"].aparte = True  # la plantilla lo dibuja como tarjetas para elegir

    def clean(self):
        datos = super().clean()
        if datos.get("motivo") == "otro" and len((datos.get("detalle") or "").strip()) < 5:
            self.add_error("detalle", "Cuenta brevemente el motivo (al menos 5 letras).")
        return datos

    def texto_motivo(self):
        motivo = dict(self.MOTIVOS)[self.cleaned_data["motivo"]]
        detalle = (self.cleaned_data.get("detalle") or "").strip()
        return f"{motivo}. {detalle}" if detalle else motivo
