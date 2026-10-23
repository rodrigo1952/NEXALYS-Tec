"""
Elimina las tiendas suspendidas hace más de 90 días (conservando sus ventas anónimas)
y las cuentas de cliente que no confirmaron su correo en 7 días.

Uso:  python manage.py limpiar_cuentas
La misma limpieza se hace sola cuando un administrador entra al panel. Este comando
sirve para programarla en el servidor (por ejemplo, una vez al día) cuando la página
se publique.
"""

from django.core.management.base import BaseCommand

from administracion import limpieza


class Command(BaseCommand):
    help = "Elimina tiendas suspendidas hace 90 días y cuentas sin confirmar hace 7 días."

    def handle(self, *args, **opciones):
        tiendas, cuentas = limpieza.ejecutar()
        self.stdout.write(self.style.SUCCESS(
            f"Tiendas eliminadas: {tiendas}. Cuentas sin confirmar eliminadas: {cuentas}."
        ))
