from django.contrib import admin

from .models import Categoria, FotoProducto, Marca, Producto


class FotoProductoInline(admin.TabularInline):
    model = FotoProducto
    extra = 0


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activa")
    list_editable = ("activa",)
    search_fields = ("nombre",)


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activa")
    list_editable = ("activa",)
    search_fields = ("nombre",)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tienda", "categoria", "marca", "precio", "precio_oferta", "stock", "activo", "destacado")
    list_filter = ("activo", "destacado", "categoria", "marca", "tienda")
    inlines = (FotoProductoInline,)
    search_fields = ("nombre", "tienda__nombre")
    list_select_related = ("tienda", "categoria", "marca")
