from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("", views.catalogo, name="catalogo"),
    path("producto/<int:pk>/", views.producto_detalle, name="detalle"),
    path("mis-productos/", views.mis_productos, name="mis_productos"),
    path("mis-productos/nuevo/", views.producto_crear, name="crear"),
    path("mis-productos/<int:pk>/editar/", views.producto_editar, name="editar"),
    path("mis-productos/<int:pk>/eliminar/", views.producto_eliminar, name="eliminar"),
]
