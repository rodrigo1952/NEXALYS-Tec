"""
Vuelve a una copia de seguridad: reemplaza la base de datos y copia las fotos.

Uso (con la página DETENIDA):
    python manage.py restaurar_copia copias/nexalys-copia-20261111-030000.zip --confirmar
La base de datos actual se guarda antes como db.sqlite3.antes-de-restaurar.
"""

from django.core.management.base import BaseCommand, CommandError

from administracion import copias


class Command(BaseCommand):
    help = "Restaura una copia de seguridad (.zip creado por copia_seguridad)."

    def add_arguments(self, parser):
        parser.add_argument("archivo", help="Ruta del .zip de la copia")
        parser.add_argument("--confirmar", action="store_true", help="Confirma que quieres reemplazar los datos actuales")

    def handle(self, archivo, confirmar=False, **opciones):
        if not confirmar:
            raise CommandError(
                "Esto REEMPLAZA la base de datos actual por la de la copia. "
                "Detén la página y vuelve a ejecutarlo con --confirmar."
            )
        try:
            fotos = copias.restaurar(archivo)
        except FileNotFoundError:
            raise CommandError(f"No existe el archivo {archivo}.")
        except (ValueError, OSError) as error:
            raise CommandError(str(error))
        self.stdout.write(self.style.SUCCESS(
            f"Listo: se restauró la base de datos y {fotos} foto(s). "
            "La base anterior quedó como db.sqlite3.antes-de-restaurar. Ahora vuelve a iniciar la página."
        ))
