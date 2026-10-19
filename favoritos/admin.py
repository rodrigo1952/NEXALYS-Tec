from django.contrib import admin

from .models import Favorito


@admin.register(Favorito)
class FavoritoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "producto", "precio_guardado", "creado")
    list_filter = ("producto__tienda",)
    search_fields = ("usuario__username", "producto__nombre")
    list_select_related = ("usuario", "producto")
