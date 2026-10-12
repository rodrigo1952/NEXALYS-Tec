from django.contrib import admin

from .models import Pedido


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "tienda", "producto", "cliente_nombre", "cantidad", "precio_unitario", "estado", "creado")
    list_filter = ("estado", "tienda")
    search_fields = ("cliente_nombre", "cliente_telefono", "producto__nombre")
    list_select_related = ("tienda", "producto")
    # El stock se controla desde la aplicación; aquí solo se consulta para no descuadrarlo.
    readonly_fields = [f.name for f in Pedido._meta.fields]

    def has_add_permission(self, request):
        return False
