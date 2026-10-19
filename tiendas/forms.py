import re
from datetime import time

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError

from cuentas.estilos import EstiloBootstrapMixin

from .models import HorarioDia, Tienda, validar_whatsapp


def normalizar_whatsapp(valor):
    """Quita espacios, guiones y el prefijo +51 para guardar solo los 9 dígitos."""
    numero = re.sub(r"[\s\-()]", "", valor or "")
    if numero.startswith("+51"):
        numero = numero[3:]
    elif numero.startswith("51") and len(numero) == 11:
        numero = numero[2:]
    return numero


class RegistroTiendaForm(EstiloBootstrapMixin, UserCreationForm):
    """CU-01 Registrar tienda: crea el usuario y su tienda en un solo paso."""

    nombre_tienda = forms.CharField(label="Nombre de la tienda", max_length=100)
    direccion = forms.CharField(
        label="Dirección",
        max_length=200,
        help_text="Dirección del local, con referencia si es posible.",
    )
    whatsapp = forms.CharField(
        label="WhatsApp",
        max_length=16,
        help_text="Celular de 9 dígitos. Por aquí te escribirán los clientes.",
    )
    descripcion = forms.CharField(
        label="Descripción",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Opcional: qué vende tu tienda, horario de atención, etc.",
    )
    email = forms.EmailField(
        label="Correo electrónico",
        help_text="Te enviaremos un enlace para verificar tu tienda.",
    )

    field_order = [
        "nombre_tienda",
        "direccion",
        "whatsapp",
        "descripcion",
        "username",
        "email",
        "password1",
        "password2",
    ]

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_nombre_tienda(self):
        nombre = " ".join(self.cleaned_data["nombre_tienda"].split())
        if Tienda.objects.filter(nombre__iexact=nombre).exists():
            raise ValidationError("Ya existe una tienda registrada con ese nombre.")
        return nombre

    def clean_whatsapp(self):
        numero = normalizar_whatsapp(self.cleaned_data["whatsapp"])
        validar_whatsapp(numero)
        if Tienda.objects.filter(whatsapp=numero).exists():
            raise ValidationError("Ese número de WhatsApp ya pertenece a otra tienda.")
        return numero

    def clean_email(self):
        correo = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=correo).exists():
            raise ValidationError("Ese correo ya está registrado.")
        return correo

    def save(self, commit=True):
        usuario = super().save(commit=True)
        grupo, _ = Group.objects.get_or_create(name="Tienda")
        usuario.groups.add(grupo)
        Tienda.objects.create(
            usuario=usuario,
            nombre=self.cleaned_data["nombre_tienda"],
            direccion=self.cleaned_data["direccion"].strip(),
            whatsapp=self.cleaned_data["whatsapp"],
            descripcion=self.cleaned_data["descripcion"].strip(),
        )
        return usuario


class EditarTiendaForm(EstiloBootstrapMixin, forms.ModelForm):
    """La tienda edita sus propios datos desde su panel."""

    # Se acepta el número con +51 o espacios; se guardan solo los 9 dígitos.
    whatsapp = forms.CharField(
        label="WhatsApp",
        max_length=16,
        help_text="Celular de 9 dígitos. Por aquí te escriben los clientes.",
    )

    class Meta:
        model = Tienda
        fields = ["nombre", "direccion", "whatsapp", "descripcion", "logo"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split())
        if Tienda.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Ya existe una tienda registrada con ese nombre.")
        return nombre

    def clean_direccion(self):
        return " ".join(self.cleaned_data["direccion"].split())

    def clean_whatsapp(self):
        numero = normalizar_whatsapp(self.cleaned_data["whatsapp"])
        validar_whatsapp(numero)
        if Tienda.objects.filter(whatsapp=numero).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Ese número de WhatsApp ya pertenece a otra tienda.")
        return numero


HORAS_12 = [("", "—")] + [
    (f"{hora}:{minuto:02d}", f"{hora}:{minuto:02d}")
    for hora in list(range(1, 13))
    for minuto in (0, 30)
]
PERIODOS = [("", "—"), ("am", "a. m."), ("pm", "p. m.")]


class HoraAmPmWidget(forms.MultiWidget):
    """Dos listas: la hora (1:00 … 12:30) y si es a. m. o p. m."""

    def __init__(self, attrs=None):
        clase = {"class": "form-select form-select-sm"}
        super().__init__(
            [
                forms.Select(choices=HORAS_12, attrs={**clase, "aria-label": "Hora"}),
                forms.Select(choices=PERIODOS, attrs={**clase, "aria-label": "a. m. o p. m."}),
            ],
            attrs,
        )

    def decompress(self, valor):
        if not valor:
            return ["", ""]
        return [f"{valor.hour % 12 or 12}:{valor.minute:02d}", "am" if valor.hour < 12 else "pm"]


class HoraAmPmField(forms.MultiValueField):
    """
    Convierte lo elegido en las dos listas a una hora: ("9:00", "pm") -> 21:00.
    Ambas vacías = sin hora. Si falta una de las dos, se pide completarla.
    """

    widget = HoraAmPmWidget

    def __init__(self, **kwargs):
        campos = (
            forms.ChoiceField(choices=HORAS_12, required=False),
            forms.ChoiceField(choices=PERIODOS, required=False),
        )
        super().__init__(campos, require_all_fields=False, required=False, **kwargs)

    def compress(self, valores):
        hora, periodo = (list(valores) + ["", ""])[:2]
        if not hora and not periodo:
            return None
        if not hora:
            raise ValidationError("Elige la hora.")
        if not periodo:
            raise ValidationError("Elige si es a. m. o p. m.")
        horas, minutos = (int(parte) for parte in hora.split(":"))
        if periodo == "am":
            horas = 0 if horas == 12 else horas  # 12:00 a. m. = medianoche
        else:
            horas = 12 if horas == 12 else horas + 12  # 12:00 p. m. = mediodía
        return time(horas, minutos)


class HorarioForm(EstiloBootstrapMixin, forms.Form):
    """
    Horario de atención de lunes a domingo.
    - Abre y cierra: si se dejan vacías, ese día la tienda no atiende.
    - Refrigerio (opcional): el descanso del mediodía, p. ej. de 1:00 p. m. a 3:00 p. m.
    """

    CAMPOS = (
        ("abre", "abre"),
        ("descanso_inicio", "refrigerio desde"),
        ("descanso_fin", "refrigerio hasta"),
        ("cierra", "cierra"),
    )

    def __init__(self, *args, tienda, **kwargs):
        super().__init__(*args, **kwargs)
        actuales = {h.dia: h for h in tienda.horarios.all()}
        for dia, nombre in HorarioDia.Dia.choices:
            horario = actuales.get(dia)
            for campo, etiqueta in self.CAMPOS:
                self.fields[f"{campo}_{dia}"] = HoraAmPmField(
                    label=f"{nombre} ({etiqueta})",
                    initial=getattr(horario, campo, None),
                )

    def dias(self):
        """Para la plantilla: (nombre del día, abre, refrigerio desde, refrigerio hasta, cierra)."""
        for dia, nombre in HorarioDia.Dia.choices:
            yield (nombre, *(self[f"{campo}_{dia}"] for campo, _ in self.CAMPOS))

    def clean(self):
        datos = super().clean()
        for dia, _nombre in HorarioDia.Dia.choices:
            abre, cierra = datos.get(f"abre_{dia}"), datos.get(f"cierra_{dia}")
            desde, hasta = datos.get(f"descanso_inicio_{dia}"), datos.get(f"descanso_fin_{dia}")

            if (abre is None) != (cierra is None):
                campo = f"cierra_{dia}" if cierra is None else f"abre_{dia}"
                self.add_error(campo, "Completa la hora de apertura y la de cierre, o deja ambas vacías si ese día no abres.")
                continue
            if abre is not None and cierra <= abre:
                self.add_error(f"cierra_{dia}", "La hora de cierre debe ser después de la de apertura.")
                continue

            if desde is None and hasta is None:
                continue
            if abre is None:
                self.add_error(f"descanso_inicio_{dia}", "Indica primero a qué hora abres y cierras ese día.")
            elif (desde is None) != (hasta is None):
                campo = f"descanso_fin_{dia}" if hasta is None else f"descanso_inicio_{dia}"
                self.add_error(campo, "Completa el inicio y el fin del refrigerio, o deja ambos vacíos.")
            elif not (abre < desde < hasta < cierra):
                self.add_error(
                    f"descanso_inicio_{dia}",
                    "El refrigerio debe estar dentro del horario: después de abrir y antes de cerrar.",
                )
        return datos

    def save(self, tienda):
        for dia, _nombre in HorarioDia.Dia.choices:
            HorarioDia.objects.update_or_create(
                tienda=tienda,
                dia=dia,
                defaults={campo: self.cleaned_data.get(f"{campo}_{dia}") for campo, _ in self.CAMPOS},
            )
