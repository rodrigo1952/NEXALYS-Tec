from django.urls import path

from . import gestion, views

app_name = "catalogo"

urlpatterns = [
    path("", views.catalogo, name="catalogo"),
    path("producto/<int:pk>/", views.producto_detalle, name="detalle"),
    path("mis-productos/", views.mis_productos, name="mis_productos"),
    path("mis-productos/nuevo/", views.producto_crear, name="crear"),
    path("mis-productos/<int:pk>/editar/", views.producto_editar, name="editar"),
    path("mis-productos/<int:pk>/eliminar/", views.producto_eliminar, name="eliminar"),
    # CU-07: gestión de categorías y marcas (solo Administrador)
    path("gestion/<str:tipo>/", gestion.gestion_lista, name="gestion_lista"),
    path("gestion/<str:tipo>/nuevo/", gestion.gestion_crear, name="gestion_crear"),
    path("gestion/<str:tipo>/<int:pk>/editar/", gestion.gestion_editar, name="gestion_editar"),
    path("gestion/<str:tipo>/<int:pk>/eliminar/", gestion.gestion_eliminar, name="gestion_eliminar"),
]
