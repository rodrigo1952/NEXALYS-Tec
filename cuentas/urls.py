from django.urls import path

from administracion.views import resumen

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("registro/", views.registro, name="registro"),
    path("registro/confirma-tu-correo/", views.confirmacion_pendiente, name="confirmacion_pendiente"),
    path("registro/reenviar-enlace/", views.reenviar_confirmacion, name="reenviar_confirmacion"),
    path("registro/confirmar/<str:token>/", views.confirmar_correo, name="confirmar_correo"),
    path("mi-cuenta/", views.mi_cuenta, name="mi_cuenta"),
    path("mi-cuenta/editar/", views.editar_datos, name="editar_datos"),
    path("mi-cuenta/eliminar/", views.eliminar_cuenta, name="eliminar_cuenta"),
    path("mi-cuenta/nueva-clave/", views.clave_temporal, name="clave_temporal"),
    path("ayuda/", views.ayuda, name="ayuda"),
    path("privacidad/", views.privacidad, name="privacidad"),
    path("privacidad/aceptar/", views.privacidad_aceptar, name="privacidad_aceptar"),
    path("privacidad/solicitud/", views.privacidad_solicitud, name="privacidad_solicitud"),
    path("mi-cuenta/mis-datos/", views.mis_datos, name="mis_datos"),
    path("panel/admin/", resumen, name="panel_admin"),  # portada del panel de administración
]
