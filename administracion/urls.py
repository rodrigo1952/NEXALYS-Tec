from django.urls import path

from . import views

app_name = "administracion"

urlpatterns = [
    path("tiendas/", views.tiendas, name="tiendas"),
    path("tiendas/<int:pk>/", views.tienda_detalle, name="tienda_detalle"),
    path("tiendas/<int:pk>/suspender/", views.tienda_suspender, name="tienda_suspender"),
    path("tiendas/<int:pk>/reactivar/", views.tienda_reactivar, name="tienda_reactivar"),
    path("productos/", views.productos, name="productos"),
    path("productos/<int:pk>/ocultar/", views.producto_ocultar, name="producto_ocultar"),
    path("productos/<int:pk>/mostrar/", views.producto_mostrar, name="producto_mostrar"),
    path("ventas/", views.ventas, name="ventas"),
    path("usuarios/", views.usuarios, name="usuarios"),
    path("usuarios/<int:pk>/desactivar/", views.usuario_desactivar, name="usuario_desactivar"),
    path("usuarios/<int:pk>/reactivar/", views.usuario_reactivar, name="usuario_reactivar"),
    path("usuarios/<int:pk>/eliminar/", views.usuario_eliminar, name="usuario_eliminar"),
    path("usuarios/<int:pk>/clave/", views.usuario_clave, name="usuario_clave"),
    path("historial/", views.historial, name="historial"),
]
