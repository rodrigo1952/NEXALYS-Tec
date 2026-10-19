from django.urls import path

from administracion.views import resumen

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("registro/", views.registro, name="registro"),
    path("mi-cuenta/", views.mi_cuenta, name="mi_cuenta"),
    path("mi-cuenta/editar/", views.editar_datos, name="editar_datos"),
    path("mi-cuenta/eliminar/", views.eliminar_cuenta, name="eliminar_cuenta"),
    path("panel/admin/", resumen, name="panel_admin"),  # portada del panel de administración
]
