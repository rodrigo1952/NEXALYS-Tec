from django import forms
from django.conf import settings
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse

from .estilos import EstiloBootstrapMixin
from .reautenticacion import ConfirmarClaveMixin


class IngresoForm(AuthenticationForm):
    """
    Inicio de sesión que explica por qué una cuenta desactivada no puede entrar.

    Django rechaza las cuentas desactivadas con el mismo mensaje que una contraseña
    incorrecta. Aquí, SOLO si la contraseña es correcta, se avisa que la cuenta fue
    desactivada y se muestra el motivo que escribió el administrador. Con una
    contraseña incorrecta no se revela nada sobre la cuenta.

    Además, el selector "Soy cliente / Soy tienda" se valida: una cuenta de tienda
    debe entrar como tienda y una de cliente como cliente (el administrador puede
    entrar con cualquiera). El aviso solo aparece si la contraseña es correcta.
    """

    TIPOS = (("cliente", "Soy cliente"), ("tienda", "Soy tienda"))
    # Si no llega (formularios antiguos o pruebas), no se valida el tipo de cuenta.
    tipo = forms.ChoiceField(choices=TIPOS, required=False, widget=forms.RadioSelect)

    cuenta_desactivada = False
    motivo_desactivacion = ""
    correo_sin_confirmar = False
    tipo_equivocado = ""  # "tienda" o "cliente": el tipo con el que SÍ debe entrar
    clave_vencida = False  # entró con una clave temporal que ya venció

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control", "placeholder": "Tu nombre de usuario"})
        self.fields["password"].widget.attrs.update({"class": "form-control", "placeholder": "Tu contraseña"})
        # Si venía de una página de la tienda (ej.: /inventario/), ya se marca "Soy tienda".
        siguiente = self.request.GET.get("next", "") if self.request else ""
        paginas_de_tienda = ("/tiendas/panel", "/inventario/", "/catalogo/mis-productos")
        self.fields["tipo"].initial = "tienda" if siguiente.startswith(paginas_de_tienda) else "cliente"

    def clean(self):
        datos = self._validar_clave()
        self._validar_tipo()
        self._validar_clave_temporal()
        return datos

    def _validar_clave_temporal(self):
        """Una clave temporal del administrador sirve solo 24 horas."""
        from .clave_temporal import vigente

        usuario = self.get_user()
        registro = vigente(usuario) if usuario is not None else None
        if registro is not None and registro.vencida():
            self.clave_vencida = True
            raise ValidationError(
                "Tu clave temporal venció (duraba 24 horas). Pide otra al administrador.", code="clave_vencida"
            )

    def _validar_tipo(self):
        tipo = self.cleaned_data.get("tipo")
        usuario = self.get_user()
        if not tipo or usuario is None:
            return
        if usuario.is_superuser or usuario.groups.filter(name="Administrador").exists():
            return
        es_tienda = hasattr(usuario, "tienda")
        if tipo == "tienda" and not es_tienda:
            self.tipo_equivocado = "cliente"
            raise ValidationError("Esta cuenta es de cliente. Elige «Soy cliente» para entrar.", code="tipo_cliente")
        if tipo == "cliente" and es_tienda:
            self.tipo_equivocado = "tienda"
            raise ValidationError("Esta cuenta es de una tienda. Elige «Soy tienda» para entrar.", code="tipo_tienda")

    def _validar_clave(self):
        try:
            return super().clean()
        except ValidationError:
            nombre = self.cleaned_data.get("username")
            clave = self.cleaned_data.get("password")
            usuario = User.objects.filter(username=nombre).first() if nombre else None
            if usuario is not None and not usuario.is_active and clave and usuario.check_password(clave):
                from administracion.acciones import motivo_desactivacion

                from .models import CorreoPendiente

                if CorreoPendiente.objects.filter(usuario=usuario).exists():
                    self.correo_sin_confirmar = True  # todavía no abrió el enlace del correo
                else:
                    self.cuenta_desactivada = True
                    self.motivo_desactivacion = motivo_desactivacion(usuario) or ""
            raise


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


class PerfilForm(ConfirmarClaveMixin, EstiloBootstrapMixin, forms.ModelForm):
    """
    Editar datos personales. Regla: para cambiar el nombre o el correo se pide la
    contraseña actual (el correo es por donde llega "Olvidé mi contraseña").
    No se vuelve a pedir durante 10 minutos (cuentas/reautenticacion.py).
    """

    CAMPOS_SENSIBLES = {"first_name": "nombres", "last_name": "apellidos", "email": "correo"}

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

    def valor_original(self, campo):
        valor = getattr(self.instance, campo) or ""
        return valor.lower() if campo == "email" else valor

    def clean_email(self):
        correo = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=correo).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Ese correo ya está registrado.")
        return correo



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
