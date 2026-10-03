from django.urls import path

from . import views

app_name = "tiendas"

urlpatterns = [
    path("registro/", views.registro_tienda, name="registro"),
    path("verificar/<str:token>/", views.verificar, name="verificar"),
    path("reenviar-verificacion/", views.reenviar_verificacion, name="reenviar"),
    path("panel/", views.panel, name="panel"),
    path("<int:pk>/", views.perfil, name="perfil"),
]
