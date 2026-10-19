from django.urls import path

from . import views

app_name = "favoritos"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("<int:pk>/alternar/", views.alternar, name="alternar"),
    path("<int:pk>/guardar/", views.guardar_despues, name="guardar_despues"),
]
