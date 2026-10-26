from django.contrib import admin

from .models import FichaInventario, Ingreso, Movimiento, Proveedor, Venta


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    """El kardex solo se consulta: se corrige con un nuevo movimiento, nunca editando."""

    list_display = ("fecha", "tienda_nombre", "producto_nombre", "tipo", "cantidad", "stock_resultante")
    list_filter = ("tipo",)
    search_fields = ("producto_nombre", "tienda_nombre")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(FichaInventario)
admin.site.register(Proveedor)
admin.site.register(Venta)
admin.site.register(Ingreso)
