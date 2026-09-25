from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("registro/", views.registro, name="registro"),
    path("mi-cuenta/", views.mi_cuenta, name="mi_cuenta"),
    path("panel/admin/", views.panel_admin, name="panel_admin"),
    path("panel/ventas/", views.panel_vendedor, name="panel_vendedor"),
]