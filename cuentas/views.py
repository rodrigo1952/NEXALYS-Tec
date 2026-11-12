import logging
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView, PasswordResetView
from django.core.exceptions import NON_FIELD_ERRORS, PermissionDenied, ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from catalogo.destacados import destacados_en_turnos
from catalogo.models import Producto
from favoritos.permisos import es_cliente

from . import limites
from .clave_temporal import CLAVE_SESION
from .concurrencia import validar_y_guardar
from .forms import EliminarCuentaForm, IngresoForm, NuevaClaveForm, PerfilForm, RecuperarClaveForm, RegistroForm
from .models import DIAS_PARA_CONFIRMAR_CORREO, ClaveTemporal, CorreoPendiente
from .reautenticacion import confirmada_recientemente, marcar_confirmada
from .verificacion import enviar_correo_confirmacion, horas_validez, leer_token

logger = logging.getLogger(__name__)


def tiene_rol(user, *roles):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=roles).exists()


def rol_requerido(*roles):
    """Permite el acceso solo a usuarios con alguno de los roles indicados."""
    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            if not tiene_rol(request.user, *roles):
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador


def inicio(request):
    visibles = Producto.objects.visibles().select_related("tienda", "marca", "categoria")
    destacados, total_destacados = destacados_en_turnos(visibles)
    return render(request, "inicio.html", {
        # 8 lugares repartidos por turnos entre las tiendas (ver catalogo/destacados.py).
        "destacados": destacados,
        "total_destacados": total_destacados,
        # Ofertas: primero el mayor descuento.
        "ofertas": visibles.ofertas_inicio()[:8],
        "recientes": visibles[:8],
    })


def registro(request):
    if request.user.is_authenticated:
        return redirect("inicio")

    if request.method == "POST":
        form = RegistroForm(request.POST)
        # Regla de negocio: la cuenta queda inactiva hasta que el cliente confirme su correo.
        form.instance.is_active = False
        usuario = validar_y_guardar(form)
        if usuario:
            grupo, _ = Group.objects.get_or_create(name="Cliente")
            usuario.groups.add(grupo)
            CorreoPendiente.objects.create(usuario=usuario)
            # Prueba del consentimiento (Ley 29733): versión de la política, fecha y conexión.
            from .models import ConsentimientoPrivacidad
            from .privacidad import registrar_aceptacion

            registrar_aceptacion(request, usuario, ConsentimientoPrivacidad.Origen.REGISTRO_CLIENTE)
            _enviar_confirmacion(request, usuario)
            request.session["correo_por_confirmar"] = usuario.email
            return redirect("confirmacion_pendiente")
    else:
        form = RegistroForm()

    return render(request, "cuentas/registro.html", {"form": form})


def _enviar_confirmacion(request, usuario):
    try:
        enviar_correo_confirmacion(request, usuario)
        return True
    except Exception:  # p. ej. el servidor de correo no responde
        logger.exception("No se pudo enviar el correo de confirmación")
        messages.error(request, "No pudimos enviar el correo. Inténtalo de nuevo con el botón \"Reenviar enlace\".")
        return False


def _pagina_confirmacion(request, enlace_invalido=False, status=200):
    return render(request, "cuentas/confirmar_correo.html", {
        "correo": request.session.get("correo_por_confirmar", ""),
        "horas": horas_validez(),
        "dias": DIAS_PARA_CONFIRMAR_CORREO,
        "enlace_invalido": enlace_invalido,
    }, status=status)


def confirmacion_pendiente(request):
    """Después de registrarse: "Revisa tu correo", con opción de reenviar el enlace."""
    return _pagina_confirmacion(request)


@require_POST
def reenviar_confirmacion(request):
    correo = request.POST.get("email", "").strip()
    espera = limites.segundos_de_espera(limites.CORREO_CONFIRMACION, request, correo)
    if espera:
        request.session["correo_por_confirmar"] = correo
        messages.error(request, limites.mensaje_de_espera(espera))
        return redirect("confirmacion_pendiente")
    limites.anotar(limites.CORREO_CONFIRMACION, request, correo)
    usuario = (
        User.objects.filter(email__iexact=correo, is_active=False, correo_pendiente__isnull=False).first()
        if correo else None
    )
    if usuario is not None:
        _enviar_confirmacion(request, usuario)
    request.session["correo_por_confirmar"] = correo
    # Mismo mensaje exista o no la cuenta: así no se revela qué correos están registrados.
    messages.info(request, "Si ese correo corresponde a una cuenta sin confirmar, te enviamos un enlace nuevo.")
    return redirect("confirmacion_pendiente")


def confirmar_correo(request, token):
    """El cliente abre el enlace del correo: su cuenta se activa y entra directamente."""
    usuario_id = leer_token(token)
    usuario = User.objects.filter(pk=usuario_id).first() if usuario_id else None
    if usuario is None:
        return _pagina_confirmacion(request, enlace_invalido=True, status=400)
    pendiente = CorreoPendiente.objects.filter(usuario=usuario).first()
    if pendiente is None:
        messages.info(request, "Tu correo ya estaba confirmado. Inicia sesión.")
        return redirect("login")
    usuario.is_active = True
    usuario.save(update_fields=["is_active"])
    pendiente.delete()
    request.session.pop("correo_por_confirmar", None)
    login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, "¡Correo confirmado! Bienvenido a NEXALYS Tec.")
    return redirect("inicio")


@login_required
def mi_cuenta(request):
    """Mi cuenta (para todos los roles): datos personales, editar datos y cambiar contraseña."""
    return render(request, "cuentas/mi_cuenta.html", {
        "puede_eliminar": _puede_eliminar_cuenta(request.user),
        "total_favoritos": request.user.favoritos.count(),
    })


@login_required
def editar_datos(request):
    form = PerfilForm(
        request.POST if request.method == "POST" else None, instance=request.user,
        usuario=request.user, ya_confirmada=confirmada_recientemente(request),
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        if form.clave_confirmada:
            marcar_confirmada(request)
        messages.success(request, "Tus datos se actualizaron correctamente.")
        return redirect("mi_cuenta")
    return render(request, "cuentas/editar_datos.html", {"form": form})


def _puede_eliminar_cuenta(user):
    """
    Regla: solo los Clientes eliminan su cuenta desde la página. Una Tienda tiene
    productos y ventas, y el administrador no se elimina a sí mismo.
    """
    return es_cliente(user) and not user.is_superuser and getattr(user, "tienda", None) is None


@login_required
def eliminar_cuenta(request):
    """Ley de Protección de Datos Personales: el cliente puede borrar su cuenta y sus datos."""
    if not _puede_eliminar_cuenta(request.user):
        raise PermissionDenied

    form = EliminarCuentaForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = request.user
        logout(request)
        usuario.delete()  # también borra sus favoritos (CASCADE)
        messages.success(request, "Tu cuenta y tus datos fueron eliminados. ¡Gracias por usar NEXALYS Tec!")
        return redirect("inicio")
    return render(request, "cuentas/eliminar_cuenta.html", {"form": form})

# ---------------------------------------------------------------------------
# Ayuda y soporte / Privacidad y términos (menú de la cuenta)
# ---------------------------------------------------------------------------

CORREO_SOPORTE = settings.CORREO_SOPORTE  # CORREO_SOPORTE en el .env


def ayuda(request):
    """Preguntas frecuentes según el rol y contacto de soporte."""
    return render(request, "cuentas/ayuda.html", {"correo_soporte": CORREO_SOPORTE})


def privacidad(request):
    """Política de privacidad (Ley 29733: los 10 puntos que hay que informar) y reglas de uso."""
    from .privacidad import PLAZOS, VERSION_POLITICA, datos_titular

    return render(request, "cuentas/privacidad.html", {
        "correo_soporte": CORREO_SOPORTE,
        "titular": datos_titular(),
        "version": VERSION_POLITICA,
        "plazos": PLAZOS,
        "dias_sesion": settings.SESSION_COOKIE_AGE // 86400,
    })


def privacidad_aceptar(request):
    """Cuentas anteriores a la casilla o política nueva: aceptar la política vigente para seguir."""
    from .forms import AceptarPoliticaForm
    from .models import ConsentimientoPrivacidad
    from .privacidad import VERSION_POLITICA, acepto_version_vigente, registrar_aceptacion

    if not request.user.is_authenticated:
        return redirect("privacidad")
    siguiente = request.POST.get("next") or request.GET.get("next") or ""
    if not url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        siguiente = ""
    if acepto_version_vigente(request):
        return redirect(siguiente or destino_por_rol(request.user))
    form = AceptarPoliticaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        registrar_aceptacion(request, request.user, ConsentimientoPrivacidad.Origen.AL_ENTRAR)
        messages.success(request, "Gracias. Aceptaste la política de privacidad.")
        return redirect(siguiente or destino_por_rol(request.user))
    return render(request, "cuentas/privacidad_aceptar.html", {
        "form": form,
        "next": siguiente,
        "version": VERSION_POLITICA,
        "es_actualizacion": ConsentimientoPrivacidad.objects.filter(usuario=request.user).exists(),
        "puede_eliminar": _puede_eliminar_cuenta(request.user),
    })


def privacidad_solicitud(request):
    """Pedir un derecho sobre los datos personales. Llega a la consola con su fecha límite."""
    from .forms import SolicitudDerechoForm
    from .privacidad import PLAZOS, sumar_dias_habiles

    form = SolicitudDerechoForm(request.POST or None, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        correo = form.cleaned_data["correo"]
        espera = limites.segundos_de_espera(limites.SOLICITUD_DERECHO, request, correo)
        if espera:
            form.add_error(None, limites.mensaje_de_espera(espera))
        else:
            limites.anotar(limites.SOLICITUD_DERECHO, request, correo)
            solicitud = form.save(commit=False)
            solicitud.usuario = request.user if request.user.is_authenticated else None
            solicitud.vence = sumar_dias_habiles(timezone.localdate(), PLAZOS[solicitud.tipo])
            solicitud.save()
            _avisar_solicitud_recibida(solicitud)
            return render(request, "cuentas/privacidad_solicitud_enviada.html", {"solicitud": solicitud})
    return render(request, "cuentas/privacidad_solicitud.html", {"form": form, "plazos": PLAZOS})


def _avisar_solicitud_recibida(solicitud):
    """Constancia por correo para quien pidió (si el correo no sale, la solicitud igual queda guardada)."""
    from django.core.mail import send_mail

    try:
        send_mail(
            "Recibimos tu solicitud sobre tus datos personales | NEXALYS Tec",
            f"Hola, {solicitud.nombre}:\n\n"
            f"Recibimos tu solicitud de {solicitud.nombre_corto_tipo.lower()} el {solicitud.creada:%d/%m/%Y}.\n"
            f"Te responderemos a este correo a más tardar el {solicitud.vence:%d/%m/%Y}.\n\n"
            f"Tu pedido:\n{solicitud.detalle}\n\nNEXALYS Tec",
            None,
            [solicitud.correo],
        )
    except Exception:
        logger.exception("No se pudo enviar la constancia de la solicitud de derechos")


@login_required
def mis_datos(request):
    """Descargar mis datos (derecho de acceso): un archivo con todo lo que la página guarda de la cuenta."""
    from django.http import HttpResponse

    from .mis_datos import archivo_json

    respuesta = HttpResponse(archivo_json(request.user), content_type="application/json; charset=utf-8")
    respuesta["Content-Disposition"] = f'attachment; filename="mis-datos-nexalys-{request.user.username}.json"'
    return respuesta


class IngresoView(LoginView):
    """
    Iniciar sesión. Si la persona llegó desde un enlace (?next=...), vuelve a ese enlace;
    si no, cada rol entra a su lugar de trabajo (ver destino_por_rol).
    """

    authentication_form = IngresoForm

    def get_default_redirect_url(self):
        return destino_por_rol(self.request.user)

    # --- Límite de intentos (cuentas/limites.py): 5 contraseñas equivocadas → 15 minutos ---
    def _usuario_escrito(self):
        return self.request.POST.get("username", "")

    def _bloqueado(self, segundos):
        """Página de ingreso con el aviso de espera. No se revisa la contraseña."""
        form = self.get_form_class()(
            self.request,
            initial={"username": self._usuario_escrito(), "tipo": self.request.POST.get("tipo") or None},
        )
        contexto = self.get_context_data(form=form, bloqueo=limites.mensaje_de_espera(segundos))
        return self.render_to_response(contexto, status=429)

    def post(self, request, *args, **kwargs):
        espera = limites.segundos_de_espera(limites.LOGIN, request, self._usuario_escrito())
        if espera:
            return self._bloqueado(espera)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        limites.olvidar(limites.LOGIN, self.request, self._usuario_escrito())
        return super().form_valid(form)

    def form_invalid(self, form):
        # Solo cuenta la contraseña equivocada (no el tipo de cuenta ni una cuenta desactivada con su clave correcta).
        clave_equivocada = form.has_error(NON_FIELD_ERRORS, "invalid_login") and not (
            form.cuenta_desactivada or form.correo_sin_confirmar
        )
        if clave_equivocada:
            limites.anotar(limites.LOGIN, self.request, self._usuario_escrito())
            espera = limites.segundos_de_espera(limites.LOGIN, self.request, self._usuario_escrito())
            if espera:
                return self._bloqueado(espera)
        return super().form_invalid(form)


class RecuperarClaveView(PasswordResetView):
    """«¿Olvidaste tu contraseña?» con límite: 3 correos por hora (para el mismo correo)."""

    form_class = RecuperarClaveForm

    def form_valid(self, form):
        correo = form.cleaned_data["email"]
        espera = limites.segundos_de_espera(limites.CORREO_CLAVE, self.request, correo)
        if espera:
            form.add_error(None, limites.mensaje_de_espera(espera))
            return self.form_invalid(form)
        limites.anotar(limites.CORREO_CLAVE, self.request, correo)
        return super().form_valid(form)


def destino_por_rol(user):
    """A dónde va cada rol al entrar: administrador → consola, tienda → Mis productos, cliente → inicio."""
    if tiene_rol(user, "Administrador"):
        return reverse("panel_admin")
    if getattr(user, "tienda", None) is not None:
        return reverse("catalogo:mis_productos")
    return reverse("inicio")


class NuevaClavePropiaForm(NuevaClaveForm):
    """Crear la contraseña propia después de entrar con una clave temporal (no puede repetirla)."""

    def clean_new_password1(self):
        clave = self.cleaned_data.get("new_password1")
        if clave and self.user.check_password(clave):
            raise ValidationError("Escribe una contraseña distinta a la clave temporal.", code="misma_clave")
        return clave


@login_required
def clave_temporal(request):
    """Paso obligatorio tras entrar con una clave temporal: crear la propia contraseña."""
    if not request.session.get(CLAVE_SESION):
        return redirect(destino_por_rol(request.user))
    form = NuevaClavePropiaForm(request.user, request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        form.save()
        ClaveTemporal.objects.filter(usuario=request.user).delete()
        update_session_auth_hash(request, request.user)  # sigue con la sesión iniciada
        request.session.pop(CLAVE_SESION, None)
        messages.success(request, "¡Listo! Creaste tu nueva contraseña. Úsala desde ahora para entrar.")
        return redirect(destino_por_rol(request.user))
    return render(request, "registration/clave_temporal.html", {"form": form})
