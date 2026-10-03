from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cuentas/", include("django.contrib.auth.urls")),
    path("tiendas/", include("tiendas.urls")),
    path("catalogo/", include("catalogo.urls")),
    path("", include("cuentas.urls")),
]

# En desarrollo, Django sirve las imagenes subidas por las tiendas.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
