"""«Ampliar mapa» en Editar mi tienda (static/js/mapas.js)."""
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class MapaAmpliadoTests(SimpleTestCase):
    def test_el_mapa_ampliado_sale_de_su_tarjeta(self):
        # El vidrio (backdrop-filter) de la tarjeta encerraba al mapa «position: fixed» y la página se congelaba:
        # al ampliarlo, el editor se lleva a <body> y al reducirlo vuelve a su lugar.
        js = (Path(settings.BASE_DIR) / "static" / "js" / "mapas.js").read_text(encoding="utf-8")
        self.assertIn("document.body.appendChild(editor);", js)
        self.assertIn("lugar.parentNode.insertBefore(editor, lugar);", js)
        self.assertIn("moverEditor(abrir);", js)
