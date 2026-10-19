"""
Control de concurrencia en los registros.

Escenario: dos personas envían el formulario de registro casi al mismo tiempo
con el mismo usuario, correo, nombre de tienda o WhatsApp. Ambas validaciones
pueden pasar ("todavía no existe") y la segunda fallaría al guardar con un
error 500 (IntegrityError).

Solución:
  1. Validar y guardar dentro de una misma transacción. En SQLite, con
     transaction_mode="IMMEDIATE", la segunda espera a que termine la primera
     y entonces su validación ya ve el registro nuevo.
  2. Si aun así la base de datos rechaza un duplicado, se muestra un mensaje
     en el formulario en vez del error 500.
"""

from django.db import IntegrityError, transaction

MENSAJE_DUPLICADO = (
    "Otra persona acaba de registrarse con alguno de estos datos. "
    "Revisa el usuario, el correo, el nombre de la tienda o el WhatsApp e inténtalo de nuevo."
)


def validar_y_guardar(form):
    """Devuelve el objeto guardado, o None si el formulario no es válido o hubo un duplicado."""
    with transaction.atomic():
        if not form.is_valid():
            return None
        try:
            with transaction.atomic():  # punto de guardado: si falla, se deshace solo esto
                return form.save()
        except IntegrityError:
            form.add_error(None, MENSAJE_DUPLICADO)
            return None
