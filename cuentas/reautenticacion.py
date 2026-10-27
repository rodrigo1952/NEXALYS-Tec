"""
Confirmar la contraseña antes de guardar cambios en datos sensibles (como hacen Google o GitHub).

Datos sensibles: nombre y correo de la cuenta; nombre, dirección y WhatsApp de la tienda.
No se pide para la descripción, el logo, el horario ni para los productos.

Después de escribir la contraseña correctamente, no se vuelve a pedir durante
MINUTOS_SIN_PEDIR_CLAVE minutos (se guarda la hora en la sesión del usuario).
"""

import time

from django import forms

MINUTOS_SIN_PEDIR_CLAVE = 10
_CLAVE_SESION = "clave_confirmada_en"


def confirmada_recientemente(request):
    momento = request.session.get(_CLAVE_SESION)
    return bool(momento) and time.time() - momento < MINUTOS_SIN_PEDIR_CLAVE * 60


def marcar_confirmada(request):
    request.session[_CLAVE_SESION] = time.time()


class ConfirmarClaveMixin:
    """
    Agrega el campo "Contraseña actual" a un formulario y lo exige solo si cambió
    algún dato sensible. El formulario recibe usuario= y ya_confirmada=.

    Cada formulario define:
      CAMPOS_SENSIBLES = {"campo": "nombre que se muestra"}
      def valor_original(self, campo)  (opcional; por defecto, el del objeto que se edita)
    """

    CAMPOS_SENSIBLES = {}

    def __init__(self, *args, usuario, ya_confirmada=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.ya_confirmada = ya_confirmada
        self.clave_confirmada = False  # True si en este envío escribió bien su contraseña
        self.originales = {campo: self.valor_original(campo) for campo in self.CAMPOS_SENSIBLES}
        if not ya_confirmada:
            nombres = ", ".join(self.CAMPOS_SENSIBLES.values())
            self.fields["clave_actual"] = forms.CharField(
                label="Contraseña actual",
                required=False,
                strip=False,
                widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "class": "form-control"}),
                help_text=f"Por seguridad, es necesaria si cambias: {nombres}. "
                          f"Luego no se vuelve a pedir durante {MINUTOS_SIN_PEDIR_CLAVE} minutos.",
            )

    def valor_original(self, campo):
        return getattr(self.instance, campo, None)

    def datos_sensibles_cambiados(self):
        return [
            campo for campo in self.CAMPOS_SENSIBLES
            if campo in self.cleaned_data and self.cleaned_data[campo] != self.originales[campo]
        ]

    def clean(self):
        datos = super().clean()
        if self.ya_confirmada or not self.datos_sensibles_cambiados():
            return datos
        if self.usuario.check_password(datos.get("clave_actual") or ""):
            self.clave_confirmada = True
        else:
            self.add_error("clave_actual", "Para guardar estos cambios, escribe tu contraseña actual correctamente.")
        return datos
