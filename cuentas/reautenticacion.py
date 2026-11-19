"""
Confirmar la contraseña antes de guardar cambios en datos sensibles (como hacen Google o GitHub).

Datos sensibles: nombre y correo de la cuenta; nombre, dirección y WhatsApp de la tienda.
No se pide para la descripción, el logo, el horario ni para los productos.

Después de escribir la contraseña correctamente, no se vuelve a pedir durante
MINUTOS_SIN_PEDIR_CLAVE minutos (se guarda la hora en la sesión del usuario).

En la página, el campo se dibuja aparte, justo encima del botón «Guardar cambios»
(templates/_confirmar_clave.html), y static/js/formularios.js lo muestra apenas se
cambia un dato sensible, con el motivo («Cambiaste: ubicación en el mapa»).
"""

import time

from django import forms

MINUTOS_SIN_PEDIR_CLAVE = 10
_CLAVE_SESION = "clave_confirmada_en"


def unir(nombres):
    """["a"] -> "a"; ["a", "b"] -> "a y b"; ["a", "b", "c"] -> "a, b y c"."""
    nombres = list(nombres)
    if len(nombres) < 2:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


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
      TIPOS_SENSIBLES = {"campo": "telefono"}  (opcional; cómo compara el navegador: texto, numero, correo, telefono)
    """

    CAMPOS_SENSIBLES = {}
    TIPOS_SENSIBLES = {}

    def __init__(self, *args, usuario, ya_confirmada=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.ya_confirmada = ya_confirmada
        self.clave_confirmada = False  # True si en este envío escribió bien su contraseña
        self.originales = {campo: self.valor_original(campo) for campo in self.CAMPOS_SENSIBLES}
        if not ya_confirmada:
            nombres = ", ".join(dict.fromkeys(self.CAMPOS_SENSIBLES.values()))  # sin repetir (latitud y longitud)
            self.fields["clave_actual"] = forms.CharField(
                label="Contraseña actual",
                required=False,
                strip=False,
                widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "class": "form-control"}),
                help_text=f"Por seguridad, es necesaria si cambias: {nombres}. "
                          f"Luego no se vuelve a pedir durante {MINUTOS_SIN_PEDIR_CLAVE} minutos.",
            )
            # Se dibuja aparte, encima del botón «Guardar cambios» (templates/_confirmar_clave.html).
            self.fields["clave_actual"].aparte = True
            self.minutos_sin_pedir = MINUTOS_SIN_PEDIR_CLAVE
            self._marcar_sensibles()

    def _marcar_sensibles(self):
        """
        Cada campo sensible lleva su valor guardado y su nombre (data-sensible-*): así el
        navegador sabe cuándo cambió y muestra la contraseña con el motivo, antes de enviar.
        """
        for campo, nombre in self.CAMPOS_SENSIBLES.items():
            if campo not in self.fields:
                continue
            definicion = self.fields[campo]
            if campo in self.TIPOS_SENSIBLES:
                tipo = self.TIPOS_SENSIBLES[campo]
            elif isinstance(definicion, forms.EmailField):
                tipo = "correo"
            elif isinstance(definicion, (forms.DecimalField, forms.FloatField)):
                tipo = "numero"
            else:
                tipo = "texto"
            original = self.originales[campo]
            definicion.widget.attrs.update({
                "data-sensible": nombre,
                "data-sensible-tipo": tipo,
                "data-sensible-original": "" if original is None else str(original),
            })

    def valor_original(self, campo):
        return getattr(self.instance, campo, None)

    def datos_sensibles_cambiados(self):
        return [
            campo for campo in self.CAMPOS_SENSIBLES
            if campo in self.cleaned_data and self.cleaned_data[campo] != self.originales[campo]
        ]

    def motivos_clave(self):
        """Lo que cambió y pide la contraseña, en palabras: «dirección y ubicación en el mapa»."""
        if not hasattr(self, "cleaned_data"):
            return ""
        return unir(dict.fromkeys(self.CAMPOS_SENSIBLES[c] for c in self.datos_sensibles_cambiados()))

    def clean(self):
        datos = super().clean()
        if self.ya_confirmada or not self.datos_sensibles_cambiados():
            return datos
        clave = datos.get("clave_actual") or ""
        if self.usuario.check_password(clave):
            self.clave_confirmada = True
        elif not clave:
            self.add_error("clave_actual", "Para guardar estos cambios, escribe tu contraseña actual.")
        else:
            self.add_error("clave_actual", "La contraseña no es correcta. Para guardar estos cambios, "
                                           "escribe tu contraseña actual.")
        return datos
