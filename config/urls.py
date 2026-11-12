from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import redirect_to_login
from django.urls import include, path, reverse

from cuentas.forms import CambiarClaveForm, NuevaClaveForm
from cuentas.views import IngresoView, RecuperarClaveView


def ingreso_admin(request):
    """El Django Admin usa el mismo «Iniciar sesión» de la página (con su límite de intentos)."""
    return redirect_to_login(request.GET.get("next") or reverse("admin:index"))


urlpatterns = [
    # Django Admin en la dirección secreta del .env (DJANGO_ADMIN_URL).
    path(f"{settings.ADMIN_URL}login/", ingreso_admin),
    path(settings.ADMIN_URL, admin.site.urls),
    # Vistas de contraseña de Django con nuestros formularios (van antes del include
    # de django.contrib.auth.urls para reemplazar a las de Django).
    path(
        "cuentas/login/",
        IngresoView.as_view(),  # la tienda entra directo a «Mis productos»
        name="login",
    ),
    path(
        "cuentas/password_change/",
        auth_views.PasswordChangeView.as_view(form_class=CambiarClaveForm),
        name="password_change",
    ),
    path(
        "cuentas/password_reset/",
        RecuperarClaveView.as_view(),  # con límite de 3 correos por hora
        name="password_reset",
    ),
    path(
        "cuentas/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(form_class=NuevaClaveForm),
        name="password_reset_confirm",
    ),
    path("cuentas/", include("django.contrib.auth.urls")),
    path("tiendas/", include("tiendas.urls")),
    path("catalogo/", include("catalogo.urls")),
    path("favoritos/", include("favoritos.urls")),
    path("administracion/", include("administracion.urls")),
    path("inventario/", include("inventario.urls")),
    path("libro-de-reclamaciones/", include("reclamos.urls")),
    path("", include("cuentas.urls")),
]

# En desarrollo, Django sirve las imagenes subidas por las tiendas.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
