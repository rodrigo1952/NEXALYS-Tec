from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("productos/", views.productos, name="productos"),
    path("productos/<int:pk>/ficha/", views.ficha, name="ficha"),
    path("productos/<int:pk>/kardex/", views.kardex, name="kardex"),
    path("resumen/", views.resumen, name="resumen"),
    path("resumen/excel/", views.resumen_excel, name="resumen_excel"),
    path("ventas/", views.ventas, name="ventas"),
    path("ventas/nueva/", views.venta_nueva, name="venta_nueva"),
    path("ventas/<int:pk>/", views.venta_detalle, name="venta_detalle"),
    path("ventas/<int:pk>/anular/", views.venta_anular, name="venta_anular"),
    path("ingresos/", views.ingresos, name="ingresos"),
    path("ingresos/nuevo/", views.ingreso_nuevo, name="ingreso_nuevo"),
    path("ingresos/<int:pk>/", views.ingreso_detalle, name="ingreso_detalle"),
    path("ingresos/<int:pk>/anular/", views.ingreso_anular, name="ingreso_anular"),
    path("ajustes/", views.ajustes, name="ajustes"),
    path("ajustes/nuevo/", views.ajuste_nuevo, name="ajuste_nuevo"),
    path("conteo/", views.conteo, name="conteo"),
    path("proveedores/", views.proveedores, name="proveedores"),
    path("proveedores/nuevo/", views.proveedor_crear, name="proveedor_crear"),
    path("proveedores/<int:pk>/editar/", views.proveedor_editar, name="proveedor_editar"),
    path("proveedores/<int:pk>/eliminar/", views.proveedor_eliminar, name="proveedor_eliminar"),
]
