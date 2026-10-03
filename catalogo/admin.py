from django.contrib import admin

from .models import Categoria, Marca, Producto


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
    list_display = ("nombre", "tienda", "categoria", "marca", "precio", "stock", "activo")
    list_filter = ("activo", "categoria", "marca", "tienda")
    search_fields = ("nombre", "tienda__nombre")
    list_select_related = ("tienda", "categoria", "marca")
