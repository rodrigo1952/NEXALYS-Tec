from django.contrib import admin, messages

from .models import Tienda


@admin.register(Tienda)
class TiendaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "usuario", "whatsapp", "estado", "verificada_en", "creada_en")
    list_filter = ("estado",)
    search_fields = ("nombre", "usuario__username", "usuario__email", "whatsapp")
    readonly_fields = ("verificada_en", "creada_en")
    actions = ("suspender", "reactivar")

    @admin.action(description="Suspender tiendas seleccionadas (se ocultan del catálogo)")
    def suspender(self, request, queryset):
        cantidad = queryset.update(estado=Tienda.Estado.SUSPENDIDA)
        self.message_user(request, f"{cantidad} tienda(s) suspendida(s).", messages.WARNING)

    @admin.action(description="Reactivar tiendas seleccionadas")
    def reactivar(self, request, queryset):
        # Regla: solo vuelven a ACTIVA las que ya verificaron su correo;
        # las demás regresan a PENDIENTE hasta que lo verifiquen.
        activas = queryset.filter(verificada_en__isnull=False).update(estado=Tienda.Estado.ACTIVA)
        pendientes = queryset.filter(verificada_en__isnull=True).update(estado=Tienda.Estado.PENDIENTE)
        self.message_user(
            request,
            f"{activas} tienda(s) reactivada(s); {pendientes} siguen pendientes de verificar su correo.",
            messages.SUCCESS,
        )
