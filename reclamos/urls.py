from django.urls import path

from . import views

app_name = "reclamos"

urlpatterns = [
    path("", views.libro, name="libro"),
    path("hoja/<int:pk>/", views.hoja, name="hoja"),
    path("mi-tienda/", views.tienda_lista, name="tienda_lista"),
    path("mi-tienda/<int:pk>/", views.tienda_detalle, name="tienda_detalle"),
    path("consola/", views.consola_lista, name="consola_lista"),
    path("consola/<int:pk>/", views.consola_detalle, name="consola_detalle"),
]
