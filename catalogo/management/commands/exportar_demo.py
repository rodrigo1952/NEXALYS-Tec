"""
Guarda las tiendas, productos e imágenes de ESTA PC en la carpeta demo/ del proyecto,
para subirlos a GitHub y cargarlos en otra PC con: python manage.py cargar_demo
"""

from django.core.management.base import BaseCommand

from catalogo import demo


class Command(BaseCommand):
    help = "Exporta tiendas, productos e imágenes a la carpeta demo/ (sin clientes, pedidos ni contraseñas)."

    def add_arguments(self, parser):
        parser.add_argument("--carpeta", help="Carpeta de destino (por defecto: demo/ en el proyecto).")

    def handle(self, *args, **opciones):
        resumen = demo.exportar(opciones.get("carpeta"))
        for faltante in resumen["faltantes"]:
            self.stdout.write(self.style.WARNING(f"  No se encontró la imagen: {faltante}"))
        self.stdout.write(self.style.SUCCESS(
            f"Exportadas {resumen['tiendas']} tienda(s) y {resumen['productos']} producto(s) en la carpeta demo/."
        ))
        self.stdout.write("Ahora súbelo:  git add demo  ->  git commit -m \"Datos de demostración\"  ->  git push")
