"""
Copia de seguridad de la base de datos y las fotos (ver administracion/copias.py).

Uso:  python manage.py copia_seguridad
En PythonAnywhere se programa una vez al día en la pestaña «Tasks».
"""

from django.core.management.base import BaseCommand
from django.template.defaultfilters import filesizeformat

from administracion import copias


class Command(BaseCommand):
    help = "Crea una copia de seguridad (base de datos + fotos) en la carpeta copias/ y borra las de más de 14 días."

    def handle(self, *args, **opciones):
        copia = copias.crear()
        self.stdout.write(self.style.SUCCESS(
            f"Listo: {copia['nombre']} ({filesizeformat(copia['tamano'])}). "
            f"Hay {len(copias.listar())} copia(s) en {copias.carpeta()}."
        ))
