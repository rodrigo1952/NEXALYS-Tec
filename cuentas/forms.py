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

from django.utils.html import format_html

from .estilos import EstiloBootstrapMixin
from .models import SolicitudDerecho
from .reautenticacion import ConfirmarClaveMixin


class AceptarPrivacidadMixin:
    """
    Casilla «Acepto la política de privacidad» (Ley 29733): empieza SIN marcar y es obligatoria.
    La prueba (versión y fecha) la guarda la vista con cuentas.privacidad.registrar_aceptacion.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["acepto_privacidad"] = forms.BooleanField(
            required=True,
            label=format_html(
                'He leído y acepto la <a href="{}" target="_blank" rel="noopener">política de privacidad</a>',
                reverse("privacidad"),
            ),
            help_text=(
                "Usamos tus datos solo para tu cuenta y para que funcione la página; no los vendemos. "
                "Puedes pedir verlos, corregirlos o borrarlos cuando quieras."
            ),
            error_messages={"required": "Para crear la cuenta debes aceptar la política de privacidad."},
            widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        )


class AceptarPoliticaForm(forms.Form):
    """Para las cuentas que ya existían o cuando la política cambia: aceptar al entrar."""

    acepto = forms.BooleanField(
        required=True,
        label="He leído y acepto la política de privacidad",
        error_messages={"required": "Marca la casilla para aceptar la política y seguir."},
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )


class SolicitudDerechoForm(EstiloBootstrapMixin, forms.ModelForm):
    """Formulario para pedir un derecho sobre los datos personales (información, acceso, etc.)."""

    class Meta:
        model = SolicitudDerecho
        fields = ("nombre", "correo", "tipo", "detalle")
        widgets = {"tipo": forms.RadioSelect, "detalle": forms.Textarea(attrs={"rows": 4})}
        help_texts = {
            "detalle": "Cuéntanos qué necesitas. Si es una corrección, indica el dato correcto.",
            "correo": "Te responderemos a este correo. Si tienes cuenta, usa el correo de tu cuenta.",
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].widget.attrs["class"] = "form-check-input"
        self.fields["tipo"].choices = [c for c in self.fields["tipo"].choices if c[0]]
        if usuario is not None and usuario.is_authenticated:
            self.fields["nombre"].initial = usuario.get_full_name() or usuario.username
            self.fields["correo"].initial = usuario.email


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
            raise ValidationError("Esta cuenta es de cliente. Ya marcamos «Soy cliente»: escribe tu contraseña otra vez para entrar.", code="tipo_cliente")
        if tipo == "cliente" and es_tienda:
            self.tipo_equivocado = "tienda"
            raise ValidationError("Esta cuenta es de una tienda. Ya marcamos «Soy tienda»: escribe tu contraseña otra vez para entrar.", code="tipo_tienda")

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


class RegistroForm(AceptarPrivacidadMixin, EstiloBootstrapMixin, UserCreationForm):
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
