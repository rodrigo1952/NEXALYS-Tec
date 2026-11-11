"""
Almacenamiento de las imágenes subidas (carpeta media/), igual al de Django con un agregado:
al borrar una imagen, también se borran sus miniaturas (catalogo/imagenes.py).

Así no quedan miniaturas huérfanas al cambiar o quitar una foto, al eliminar un producto
o al renombrarlo (las fotos se mueven a otra carpeta y la miniatura se vuelve a crear).
"""

from django.core.files.storage import FileSystemStorage

from .imagenes import CARPETA_MINIATURAS, MINIATURAS, ruta_miniatura


class AlmacenamientoConMiniaturas(FileSystemStorage):
    def delete(self, name):
        super().delete(name)
        if name and not name.startswith(f"{CARPETA_MINIATURAS}/"):
            for tipo in MINIATURAS:
                super().delete(ruta_miniatura(name, tipo))
