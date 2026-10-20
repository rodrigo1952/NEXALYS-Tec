"""
Mueve las imágenes a la carpeta de su tienda y les pone el nombre del producto (Etapa 1).

Uso:
    python manage.py ordenar_imagenes --simular   (solo muestra lo que haría)
    python manage.py ordenar_imagenes             (mueve los archivos)

Desde que existe la reubicación automática, al cambiar el nombre de una tienda o de un
producto sus imágenes se mueven solas. Este comando sirve para las imágenes antiguas
(subidas antes de la Etapa 1) o si alguna vez una reubicación automática falló.
No borra ninguna imagen: copia, actualiza la base de datos y recién borra la vieja.
"""

from django.core.management.base import BaseCommand

from catalogo.archivos import ruta_foto_producto, ruta_imagen_producto, ruta_logo_tienda
from catalogo.models import FotoProducto, Producto
from catalogo.reubicar import FALTA, MOVIDA, ORDENADA, borrar_carpetas_vacias, mover_archivo
from tiendas.models import Tienda


class Command(BaseCommand):
    help = "Ordena las imágenes en una carpeta por tienda y las renombra con el nombre del producto."

    def add_arguments(self, parser):
        parser.add_argument("--simular", action="store_true", help="Solo muestra lo que haría, sin mover nada.")

    def handle(self, *args, **opciones):
        simular = opciones["simular"]
        cuenta = {MOVIDA: 0, ORDENADA: 0, FALTA: 0}

        def procesar(objeto, campo, calcular_ruta):
            antes = getattr(objeto, campo).name
            resultado = mover_archivo(objeto, campo, calcular_ruta, simular=simular)
            cuenta[resultado] += 1
            if resultado == MOVIDA:
                destino = calcular_ruta(objeto, antes.rsplit("/", 1)[-1]) if simular else getattr(objeto, campo).name
                self.stdout.write(f"  {antes}  ->  {destino}")
            elif resultado == FALTA:
                self.stdout.write(self.style.WARNING(f"  Falta el archivo: {antes} ({objeto})"))

        for producto in Producto.objects.select_related("tienda").exclude(imagen=""):
            procesar(producto, "imagen", ruta_imagen_producto)
        for foto in FotoProducto.objects.select_related("producto__tienda").exclude(imagen=""):
            procesar(foto, "imagen", ruta_foto_producto)
        for tienda in Tienda.objects.exclude(logo=""):
            procesar(tienda, "logo", ruta_logo_tienda)

        if not simular:
            for carpeta in ("productos", "tiendas"):  # carpetas antiguas o de nombres anteriores
                borrar_carpetas_vacias(carpeta)

        verbo = "Se moverían" if simular else "Se movieron"
        self.stdout.write(self.style.SUCCESS(
            f"{verbo} {cuenta[MOVIDA]} imagen(es). Ya estaban ordenadas: {cuenta[ORDENADA]}. "
            f"Archivos que no existen en esta PC: {cuenta[FALTA]}."
        ))
