"""
Qué pasa cuando se elimina una tienda, se elimine por donde se elimine: desde la consola
(Usuarios → Eliminar), la limpieza automática de suspendidas o el panel de Django Admin.
Lo llaman las señales del final de tiendas/models.py.

Antes de borrarla:
  - sus ventas se CONSERVAN ANÓNIMAS («Tienda eliminada», sin los datos del cliente), para que
    las estadísticas no cambien;
  - su kardex (movimientos de stock) se borra: es un dato privado de la tienda.
Después de borrarla (cuando el guardado terminó bien):
  - su logo se borra (las fotos de los productos se borran con cada producto, catalogo/models.py);
  - se borran sus carpetas vacías: media/tiendas/<N-nombre>/ y sus copias en media/miniaturas/.

Sus ingresos y proveedores se borran con ella (CASCADE). Las hojas de su Libro de Reclamaciones
se conservan (obligación legal): quedan sin tienda pero con su nombre.
"""

from django.db import transaction

from catalogo.archivos import carpeta_tienda
from catalogo.imagenes import CARPETA_MINIATURAS, MINIATURAS

NOMBRE_ANONIMO = "Tienda eliminada"


def anonimizar_registros(tienda):
    from inventario.models import Movimiento, Venta

    Venta.objects.filter(tienda=tienda).update(
        tienda=None, tienda_nombre=NOMBRE_ANONIMO, usuario=None,
        cliente_nombre="Cliente anónimo", cliente_documento="", nota="", motivo_anulacion="",
    )
    Movimiento.objects.filter(tienda=tienda).delete()


def carpetas_de(tienda):
    """La carpeta de la tienda y sus copias en miniaturas/ (tarjeta, icono y compartir)."""
    carpeta = carpeta_tienda(tienda)
    return [carpeta] + [f"{CARPETA_MINIATURAS}/{tipo}/{carpeta}" for tipo in MINIATURAS]


def borrar_carpetas_al_confirmar(tienda):
    """Cuando el borrado se confirma (y ya se borraron sus archivos), quita sus carpetas vacías."""
    from catalogo.reubicar import borrar_carpetas_vacias

    carpetas = carpetas_de(tienda)  # se calculan ahora: después la tienda ya no tiene número

    def borrar():
        for carpeta in carpetas:
            borrar_carpetas_vacias(carpeta)

    transaction.on_commit(borrar)
