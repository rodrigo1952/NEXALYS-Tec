"""
Carga en ESTA PC las tiendas, productos e imágenes guardados en demo/ con exportar_demo.
Lo que ya existe no se toca, así que se puede ejecutar varias veces sin duplicar nada.
"""

from django.core.management.base import BaseCommand, CommandError

from catalogo import demo


class Command(BaseCommand):
    help = "Carga los datos de demostración de la carpeta demo/."

    def add_arguments(self, parser):
        parser.add_argument("--carpeta", help="Carpeta de origen (por defecto: demo/ en el proyecto).")

    def handle(self, *args, **opciones):
        try:
            resumen = demo.cargar(opciones.get("carpeta"))
        except FileNotFoundError as error:
            raise CommandError(str(error))
        for nombre in resumen["omitidas"]:
            self.stdout.write(self.style.WARNING(f"  Ya existe en esta PC, no se tocó: {nombre}"))
        self.stdout.write(self.style.SUCCESS(
            f"Cargadas {resumen['tiendas']} tienda(s) y {resumen['productos']} producto(s)."
        ))
        if resumen["tiendas"]:
            self.stdout.write(f"Las cuentas de tienda nuevas tienen la contraseña: {demo.CLAVE_DEMO}")
        if resumen["admin_creado"]:
            self.stdout.write(f"Se creó el administrador 'admin' con la contraseña: {demo.CLAVE_DEMO}")
