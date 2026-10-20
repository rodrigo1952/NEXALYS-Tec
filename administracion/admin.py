from django.contrib import admin

from .models import AccionAdmin


@admin.register(AccionAdmin)
class AccionAdminAdmin(admin.ModelAdmin):
    """El historial solo se consulta: nadie debe poder editarlo ni borrarlo."""

    list_display = ("fecha", "admin_nombre", "tipo", "objetivo", "motivo")
    list_filter = ("tipo",)
    search_fields = ("objetivo", "motivo", "admin_nombre")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
