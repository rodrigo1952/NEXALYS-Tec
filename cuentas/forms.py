from django import forms
from django.conf import settings
from django.contrib.auth.forms import (
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse

from .estilos import EstiloBootstrapMixin


class RegistroForm(EstiloBootstrapMixin, UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True, label="Nombres")
    last_name = forms.CharField(max_length=150, required=True, label="Apellidos")
    email = forms.EmailField(required=True, label="Correo electrónico")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def clean_email(self):
        correo = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=correo).exists():
            raise ValidationError("Ese correo ya está registrado.")
        return correo


class PerfilForm(EstiloBootstrapMixin, forms.ModelForm):
    """
    Editar datos personales. Regla: para cambiar el correo se pide la contraseña
    actual, porque "Olvidé mi contraseña" envía el enlace a ese correo.
    """

    clave_actual = forms.CharField(
        label="Contraseña actual",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        help_text="Solo es necesaria si cambias tu correo.",
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        labels = {
            "first_name": "Nombres",
            "last_name": "Apellidos",
            "email": "Correo electrónico",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nombre in ("first_name", "last_name", "email"):
            self.fields[nombre].required = True
        self.correo_original = (self.instance.email or "").lower()

    def clean_email(self):
        correo = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=correo).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Ese correo ya está registrado.")
        return correo

    def clean(self):
        datos = super().clean()
        correo = datos.get("email")
        if correo and correo != self.correo_original:
            if not self.instance.check_password(datos.get("clave_actual") or ""):
                self.add_error("clave_actual", "Para cambiar tu correo, escribe tu contraseña actual correctamente.")
        return datos


class EliminarCuentaForm(EstiloBootstrapMixin, forms.Form):
    clave = forms.CharField(
        label="Contraseña actual",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    confirmar = forms.BooleanField(
        label="Entiendo que se borrarán mi cuenta y mis favoritos, y que no se puede deshacer.",
    )

    def __init__(self, usuario, *args, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

    def clean_clave(self):
        clave = self.cleaned_data["clave"]
        if not self.usuario.check_password(clave):
            raise ValidationError("La contraseña no es correcta.")
        return clave


# --- Formularios de Django para contraseñas, con estilo Bootstrap ---

class CambiarClaveForm(EstiloBootstrapMixin, PasswordChangeForm):
    pass


class NuevaClaveForm(EstiloBootstrapMixin, SetPasswordForm):
    pass


class RecuperarClaveForm(EstiloBootstrapMixin, PasswordResetForm):
    def send_mail(self, subject_template_name, email_template_name, context, *args, **kwargs):
        super().send_mail(subject_template_name, email_template_name, context, *args, **kwargs)
        # En desarrollo, el correo de la consola corta los enlaces largos con "=".
        # Por eso también se imprime el enlace completo, igual que en la verificación de tiendas.
        if settings.DEBUG:
            ruta = reverse(
                "password_reset_confirm",
                kwargs={"uidb64": context["uid"], "token": context["token"]},
            )
            print(
                f"\n[NEXALYS] Enlace para recuperar la contraseña de {context['email']}:\n"
                f"{context['protocol']}://{context['domain']}{ruta}\n"
            )
