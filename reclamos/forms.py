import re

from django import forms
from django.urls import reverse
from django.utils.html import format_html

from cuentas.estilos import EstiloBootstrapMixin
from tiendas.models import Tienda

from .models import Reclamo


class ReclamoForm(EstiloBootstrapMixin, forms.ModelForm):
    """Hoja de reclamación virtual. «dirigido_a» elige el proveedor: NEXALYS Tec o una tienda activa."""

    dirigido_a = forms.ChoiceField(label="¿A quién va dirigido?")
    acepto = forms.BooleanField(
        required=True,
        error_messages={"required": "Marca la casilla para enviar la hoja."},
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = Reclamo
        fields = (
            "nombre", "documento_tipo", "documento_numero", "domicilio", "telefono", "correo",
            "menor_de_edad", "apoderado",
            "bien", "descripcion_bien", "monto", "comprobante", "fecha_compra",
            "tipo", "detalle", "pedido",
        )
        widgets = {
            "tipo": forms.RadioSelect,
            "bien": forms.RadioSelect,
            "fecha_compra": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "detalle": forms.Textarea(attrs={"rows": 5}),
            "pedido": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "detalle": "Cuenta qué pasó, con fechas y montos si los tienes.",
            "pedido": "¿Qué solución esperas? (cambio, devolución, reparación, disculpa, etc.)",
        }

    def __init__(self, *args, tienda_inicial=None, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        tiendas = Tienda.objects.filter(estado=Tienda.Estado.ACTIVA).order_by("nombre")
        self.fields["dirigido_a"].choices = [("nexalys", "NEXALYS Tec (la página)")] + [
            (str(t.pk), f"Tienda: {t.nombre}") for t in tiendas
        ]
        self.fields["dirigido_a"].widget.attrs["class"] = "form-select"
        if tienda_inicial is not None:
            self.fields["dirigido_a"].initial = str(tienda_inicial.pk)
        for nombre in ("tipo", "bien"):
            self.fields[nombre].widget.attrs["class"] = "form-check-input"
            self.fields[nombre].choices = [c for c in self.fields[nombre].choices if c[0]]
        self.fields["acepto"].label = format_html(
            'Declaro que los datos son verdaderos y acepto que se usen solo para atender esta hoja '
            '(<a href="{}" target="_blank" rel="noopener">política de privacidad</a>).',
            reverse("privacidad"),
        )
        if usuario is not None and usuario.is_authenticated:
            self.fields["nombre"].initial = usuario.get_full_name()
            self.fields["correo"].initial = usuario.email

    def clean_documento_numero(self):
        numero = self.cleaned_data["documento_numero"].strip().upper()
        if self.cleaned_data.get("documento_tipo") == Reclamo.Documento.DNI and not re.fullmatch(r"\d{8}", numero):
            raise forms.ValidationError("El DNI tiene 8 dígitos.")
        return numero

    def clean_monto(self):
        monto = self.cleaned_data.get("monto")
        if monto is not None and monto < 0:
            raise forms.ValidationError("El monto no puede ser negativo.")
        return monto

    def clean(self):
        datos = super().clean()
        if datos.get("menor_de_edad") and not (datos.get("apoderado") or "").strip():
            self.add_error("apoderado", "Si eres menor de edad, escribe el nombre de tu padre, madre o apoderado.")
        destino = datos.get("dirigido_a")
        self.tienda_elegida = None
        if destino and destino != "nexalys":
            self.tienda_elegida = Tienda.objects.filter(pk=destino, estado=Tienda.Estado.ACTIVA).first()
            if self.tienda_elegida is None:
                self.add_error("dirigido_a", "Elige una tienda de la lista.")
        return datos


class RespuestaReclamoForm(EstiloBootstrapMixin, forms.Form):
    respuesta = forms.CharField(
        label="Respuesta (observaciones y acciones adoptadas)",
        min_length=20,
        max_length=3000,
        widget=forms.Textarea(attrs={"rows": 6, "placeholder": "Ej.: Revisamos el equipo y lo cambiamos por uno nuevo el 15/11/2026."}),
        help_text="Se envía al correo del cliente y queda en la hoja. No se puede cambiar después.",
    )
