"""
Carga las 3 tiendas de demostración y sus productos para la presentación del proyecto.
Lo que ya existe no se toca, así que se puede ejecutar varias veces sin duplicar nada.
"""

from django.core.management.base import BaseCommand

from catalogo import presentacion
from catalogo.demo import CLAVE_DEMO


class Command(BaseCommand):
    help = "Carga 3 tiendas de demostración con productos reales para la presentación."

    def handle(self, *args, **opciones):
        resumen = presentacion.cargar()
        for aviso in resumen["avisos"]:
            self.stdout.write(self.style.WARNING(f"  {aviso}"))
        for nombre in resumen["tiendas"]:
            self.stdout.write(f"  Tienda creada: {nombre}")
        if resumen["existentes"]:
            self.stdout.write(f"  {resumen['existentes']} producto(s) ya existían y no se tocaron.")
        if resumen["monitor_movido"]:
            self.stdout.write("  El 'Monitor Acer KA242Y' se pasó de Accesorios a Pantallas.")
        self.stdout.write(self.style.SUCCESS(f"Se cargaron {resumen['productos']} producto(s) nuevos."))
        if resumen["tiendas"]:
            usuarios = ", ".join(t["usuario"] for t in presentacion.TIENDAS)
            self.stdout.write(f"Usuarios de las tiendas: {usuarios} · contraseña: {CLAVE_DEMO}")
