import re
from datetime import time

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError

from cuentas.estilos import EstiloBootstrapMixin
from cuentas.reautenticacion import ConfirmarClaveMixin

from .models import HorarioDia, Tienda, hora_12, validar_whatsapp


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


class EditarTiendaForm(ConfirmarClaveMixin, EstiloBootstrapMixin, forms.ModelForm):
    """
    La tienda edita sus propios datos desde su panel. Para cambiar el nombre, la
    dirección o el WhatsApp se pide la contraseña (no para la descripción ni el logo).
    """

    CAMPOS_SENSIBLES = {"nombre": "nombre de la tienda", "direccion": "dirección", "whatsapp": "WhatsApp"}

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


class LogoForm(forms.ModelForm):
    """Solo el logo (se cambia desde el círculo del menú de la cuenta; no pide contraseña)."""

    class Meta:
        model = Tienda
        fields = ["logo"]


# ---------------------------------------------------------------------------
# Horario de atención por GRUPOS de días
# ---------------------------------------------------------------------------
# La tienda escribe un horario una sola vez y marca los días que lo usan (p. ej. lunes a sábado);
# si un día es distinto (p. ej. domingo), agrega otro grupo. Los días sin marcar quedan cerrados.
# En la base de datos se sigue guardando un HorarioDia por día (no cambia nada para el resto).

# Sugerencias cada hora (de 6:00 a. m. a 5:00 a. m. del día siguiente). Otra hora, como 8:30, se escribe.
HORAS_SUGERIDAS = [hora_12(time(h % 24)) for h in range(6, 30)]


def leer_hora(texto):
    """
    Entiende la hora como la escriben las personas: «8», «8:30», «8.30 pm», «8:30 p. m.», «20:30», «12 m».
    Devuelve un datetime.time, o lanza ValidationError con un mensaje claro.
    """
    original = (texto or "").strip()
    limpio = re.sub(r"(\d)\.(\d)", r"\1:\2", original.lower())  # 8.30 -> 8:30
    limpio = limpio.replace(".", "").replace(" ", "").replace("hrs", "").replace("h", ":")
    coincide = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?:?(am|pm|a|p|m)?", limpio)
    if not coincide:
        raise ValidationError(f"No entendimos «{original}». Escríbela así: 8:00 a. m. o 8:30 p. m.")
    horas, minutos, periodo = int(coincide.group(1)), int(coincide.group(2) or 0), coincide.group(3)
    if minutos > 59:
        raise ValidationError("Los minutos van de 00 a 59.")
    if periodo:
        if not 1 <= horas <= 12:
            raise ValidationError("Con a. m. o p. m. la hora va de 1 a 12.")
        if periodo == "m":  # «12 m.» = mediodía
            if horas != 12:
                raise ValidationError("Escribe a. m. o p. m. después de la hora.")
            return time(12, minutos)
        if periodo.startswith("a"):
            return time(0 if horas == 12 else horas, minutos)
        return time(12 if horas == 12 else horas + 12, minutos)
    if horas == 12 or 13 <= horas <= 23 or horas == 0:
        return time(horas, minutos)  # 12 = mediodía; 13 a 23 = formato de 24 horas
    raise ValidationError(f"¿{horas}:{minutos:02d} de la mañana o de la noche? Agrega a. m. o p. m.")


class HoraTextoField(forms.CharField):
    """Casilla para escribir la hora, con una lista de sugerencias cada hora (datalist)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("widget", forms.TextInput(attrs={
            "list": "horas-sugeridas", "placeholder": "ej. 8:00 a. m.", "autocomplete": "off", "maxlength": "20",
            "class": "form-control", "data-hora": "",
        }))
        super().__init__(**kwargs)

    def prepare_value(self, valor):
        return hora_12(valor) if isinstance(valor, time) else valor

    def to_python(self, valor):
        texto = super().to_python(valor)
        return leer_hora(texto) if texto else None


class GrupoHorarioForm(forms.Form):
    """Un horario y los días que lo usan. Si no tiene días ni horas, se ignora."""

    dias = forms.TypedMultipleChoiceField(
        label="Días", choices=HorarioDia.Dia.choices, coerce=int, required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "dia-chip__casilla"}),
    )
    abre = HoraTextoField(label="Abre")
    cierra = HoraTextoField(label="Cierra")
    con_refrigerio = forms.BooleanField(
        label="Cierra al mediodía (refrigerio)", required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "data-con-refrigerio": ""}),
    )
    descanso_inicio = HoraTextoField(label="Refrigerio desde")
    descanso_fin = HoraTextoField(label="hasta")

    def esta_vacio(self):
        """Sin horas escritas, el grupo no cuenta (aunque tenga días marcados): esos días quedan cerrados."""
        datos = getattr(self, "cleaned_data", {})
        return datos.get("abre") is None and datos.get("cierra") is None and not datos.get("con_refrigerio")

    def clean(self):
        datos = super().clean()
        dias, abre, cierra = datos.get("dias") or [], datos.get("abre"), datos.get("cierra")
        if self.errors or self.esta_vacio():
            return datos
        if not dias:
            self.add_error("dias", "Marca los días en que usas este horario.")
        if abre is None:
            self.add_error("abre", "Escribe a qué hora abres.")
        if cierra is None:
            self.add_error("cierra", "Escribe a qué hora cierras.")
        if abre is not None and cierra is not None and cierra <= abre:
            self.add_error("cierra", "La hora de cierre debe ser después de la de apertura.")
        if datos.get("con_refrigerio"):
            desde, hasta = datos.get("descanso_inicio"), datos.get("descanso_fin")
            if desde is None or hasta is None:
                self.add_error("descanso_inicio", "Escribe desde y hasta qué hora es el refrigerio (o desmarca la casilla).")
            elif abre is not None and cierra is not None and not (abre < desde < hasta < cierra):
                self.add_error(
                    "descanso_inicio",
                    "El refrigerio debe estar dentro del horario: después de abrir y antes de cerrar.",
                )
        else:
            datos["descanso_inicio"] = datos["descanso_fin"] = None
        return datos


class BaseGruposHorario(forms.BaseFormSet):
    def clean(self):
        if any(self.errors):
            return
        usados = {}
        for numero, form in enumerate(self.forms, start=1):
            if self.can_delete and self._should_delete_form(form):
                continue
            for dia in form.cleaned_data.get("dias") or []:
                if dia in usados:
                    raise ValidationError(
                        f"El {HorarioDia.Dia(dia).label.lower()} está marcado en el horario {usados[dia]} y en el {numero}. "
                        "Déjalo marcado solo en uno."
                    )
                usados[dia] = numero

    def save(self, tienda):
        """Guarda un HorarioDia por cada día de la semana (los días sin grupo quedan cerrados)."""
        por_dia = {}
        for form in self.forms:
            if (self.can_delete and self._should_delete_form(form)) or form.esta_vacio():
                continue
            for dia in form.cleaned_data["dias"]:
                por_dia[dia] = form.cleaned_data
        for dia, _nombre in HorarioDia.Dia.choices:
            datos = por_dia.get(dia, {})
            HorarioDia.objects.update_or_create(
                tienda=tienda, dia=dia,
                defaults={campo: datos.get(campo) for campo in ("abre", "cierra", "descanso_inicio", "descanso_fin")},
            )


GruposHorarioFormSet = forms.formset_factory(
    GrupoHorarioForm, formset=BaseGruposHorario, extra=0, max_num=7, can_delete=True,
)


def grupos_iniciales(tienda):
    """Agrupa los días que hoy tienen el mismo horario, para mostrarlos como grupos al editar."""
    grupos = {}
    for horario in tienda.horarios.all():
        if horario.abre is None:
            continue
        clave = (horario.abre, horario.cierra, horario.descanso_inicio, horario.descanso_fin)
        grupos.setdefault(clave, []).append(horario.dia)
    iniciales = [
        {"dias": dias, "abre": abre, "cierra": cierra, "con_refrigerio": desde is not None,
         "descanso_inicio": desde, "descanso_fin": hasta}
        for (abre, cierra, desde, hasta), dias in sorted(grupos.items(), key=lambda par: min(par[1]))
    ]
    # Una tienda nueva empieza con un horario típico ya marcado de lunes a sábado.
    return iniciales or [{"dias": [0, 1, 2, 3, 4, 5], "abre": None, "cierra": None}]


def horario_formset(datos, tienda):
    return GruposHorarioFormSet(datos, initial=None if datos else grupos_iniciales(tienda), prefix="horario")
