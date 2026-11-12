"""
Archivos estáticos (CSS, JS, fuentes) en TU PC (DEBUG=True).

Problema: el navegador guarda una copia de cada archivo y, sin cambio en el nombre, puede seguir usando
la vieja durante horas (había que presionar Ctrl+F5). Solución: cada enlace lleva la fecha en que se
modificó el archivo, por ejemplo  /static/js/compartir.js?v=1794456000 . Al guardar un cambio, la fecha
cambia, el enlace también, y el navegador baja la versión nueva solo.

En el servidor (DEBUG=False) no se usa: ahí ManifestStaticFilesStorage + collectstatic ponen una huella
en el nombre de cada archivo (compartir.3f2a9c1e.js), que hace lo mismo.
"""

import os

from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import StaticFilesStorage


class EstaticosConVersion(StaticFilesStorage):
    def url(self, name):
        url = super().url(name)
        ruta = finders.find(name)
        if isinstance(ruta, str) and os.path.isfile(ruta):
            url += ("&" if "?" in url else "?") + f"v={int(os.path.getmtime(ruta))}"
        return url
