from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from cuentas.forms import CambiarClaveForm, NuevaClaveForm, RecuperarClaveForm

urlpatterns = [
    path("admin/", admin.site.urls),
    # Vistas de contraseña de Django con nuestros formularios (van antes del include
    # de django.contrib.auth.urls para reemplazar a las de Django).
    path(
        "cuentas/password_change/",
        auth_views.PasswordChangeView.as_view(form_class=CambiarClaveForm),
        name="password_change",
    ),
    path(
        "cuentas/password_reset/",
        auth_views.PasswordResetView.as_view(form_class=RecuperarClaveForm),
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
    path("pedidos/", include("pedidos.urls")),
    path("favoritos/", include("favoritos.urls")),
    path("", include("cuentas.urls")),
]

# En desarrollo, Django sirve las imagenes subidas por las tiendas.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
