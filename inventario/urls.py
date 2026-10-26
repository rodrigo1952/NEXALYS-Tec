from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("productos/", views.productos, name="productos"),
    path("productos/<int:pk>/ficha/", views.ficha, name="ficha"),
    path("productos/<int:pk>/kardex/", views.kardex, name="kardex"),
    path("ventas/", views.ventas, name="ventas"),
    path("ventas/nueva/", views.venta_nueva, name="venta_nueva"),
    path("ventas/<int:pk>/", views.venta_detalle, name="venta_detalle"),
    path("ventas/<int:pk>/anular/", views.venta_anular, name="venta_anular"),
    path("proveedores/", views.proveedores, name="proveedores"),
    path("proveedores/nuevo/", views.proveedor_crear, name="proveedor_crear"),
    path("proveedores/<int:pk>/editar/", views.proveedor_editar, name="proveedor_editar"),
    path("proveedores/<int:pk>/eliminar/", views.proveedor_eliminar, name="proveedor_eliminar"),
]
