import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError

from cuentas.estilos import EstiloBootstrapMixin

from .models import Tienda, validar_whatsapp


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
