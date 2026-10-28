from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import transaction
from django.db.models import Case, IntegerField, Max, Q, Value, When
from django.db.models.functions import Lower
from django.utils import timezone

from cuentas.estilos import EstiloBootstrapMixin
from inventario.models import FichaInventario
from tiendas.models import Tienda

from .models import (
    EXTENSIONES_IMAGEN,
    MAX_DESTACADOS,
    MAX_FOTOS_EXTRA,
    PRECIO_MINIMO,
    Categoria,
    FotoProducto,
    Marca,
    Producto,
    borrar_archivo_al_confirmar,
    validar_tamano_imagen,
)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """Permite elegir varias imágenes a la vez; cada una se valida por separado."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": "image/*"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        limpiar_una = super().clean
        if isinstance(data, (list, tuple)):
            return [limpiar_una(archivo, initial) for archivo in data]
        return [limpiar_una(data, initial)] if data else []


NOMBRES_GENERICOS = ("Otra", "Otro", "Otros", "Otras")


def _otros_al_final(queryset):
    """Ordena por nombre (sin importar mayúsculas: "realme" junto a la R) y deja "Otra"/"Otros" al final."""
    return queryset.annotate(
        orden_generica=Case(When(nombre__in=NOMBRES_GENERICOS, then=Value(1)), default=Value(0), output_field=IntegerField())
    ).order_by("orden_generica", Lower("nombre"))


class ProductoForm(EstiloBootstrapMixin, forms.ModelForm):
    """Formulario del CRUD de productos (CU-03). La tienda la asigna el sistema, no el usuario."""

    # Control de concurrencia (bloqueo optimista): guarda la fecha de la última
    # modificación del producto cuando se abrió el formulario. Si al guardar ya no
    # coincide (otra pestaña lo editó o una venta cambió su stock), se avisa en vez
    # de sobrescribir los datos nuevos con los viejos.
    version = forms.CharField(widget=forms.HiddenInput, required=False)

    fotos_nuevas = MultipleImageField(
        label="Fotos adicionales",
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=EXTENSIONES_IMAGEN), validar_tamano_imagen],
        help_text=f"Opcional. Puedes elegir varias a la vez; hasta {MAX_FOTOS_EXTRA} fotos además de la principal.",
    )
    eliminar_fotos = forms.ModelMultipleChoiceField(
        label="Quitar fotos",
        queryset=FotoProducto.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    # "Hacer principal": la foto adicional elegida pasa a ser la principal y la principal
    # pasa a las adicionales (se aplica al guardar).
    principal_foto = forms.IntegerField(widget=forms.HiddenInput, required=False)

    # Precio de compra: dato PRIVADO de la tienda (es el "costo" de la ficha de inventario).
    # No es un campo de Producto: se guarda en la ficha. Se edita aquí o en la ficha; es el mismo dato.
    precio_compra = forms.DecimalField(
        label="Precio de compra (S/)", required=False, min_value=Decimal("0"), max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        help_text="Opcional. Solo tú lo ves; sirve para calcular tu ganancia.",
    )
    # Stock mínimo: también es de la ficha de inventario (el mismo dato, editable aquí o en la ficha).
    stock_minimo = forms.IntegerField(
        label="Stock mínimo", required=False, min_value=0,
        widget=forms.NumberInput(attrs={"min": "0", "placeholder": "0"}),
        help_text="Te avisamos cuando el stock llegue a este número. 0 = sin aviso.",
    )

    # Código interno (SKU): también es de la ficha. Sirve para buscar el producto o escanearlo.
    codigo = forms.CharField(
        label="Código interno", required=False, max_length=40,
        widget=forms.TextInput(attrs={"placeholder": "Ej.: LAP-ASUS-01", "autocomplete": "off"}),
        help_text="Opcional. El código que usas en tu tienda (o el del código de barras). Solo tú lo ves.",
    )

    field_order = [
        "nombre", "categoria", "marca", "codigo", "precio_compra", "precio", "precio_oferta", "oferta_hasta",
        "stock", "stock_minimo", "descripcion", "imagen", "fotos_nuevas", "activo", "destacado",
    ]

    class Meta:
        model = Producto
        fields = [
            "nombre", "categoria", "marca", "precio", "precio_oferta", "oferta_hasta",
            "stock", "descripcion", "imagen", "activo", "destacado",
        ]
        labels = {"imagen": "Foto principal", "precio": "Precio de venta (S/)", "stock": "Stock actual"}
        help_texts = {
            "stock": "Unidades que tienes hoy.",
            "precio_oferta": "Opcional. Menor que el precio de venta.",
            "oferta_hasta": "Opcional. Vacío = hasta que la quites.",
        }
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 4}),
            "precio": forms.NumberInput(attrs={"step": "0.01", "min": str(PRECIO_MINIMO)}),
            "precio_oferta": forms.NumberInput(attrs={"step": "0.01", "min": str(PRECIO_MINIMO)}),
            "oferta_hasta": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "stock": forms.NumberInput(attrs={"min": "0"}),
        }

    def __init__(self, *args, tienda, **kwargs):
        super().__init__(*args, **kwargs)
        self.tienda = tienda
        self.instance.tienda = tienda
        # Solo se ofrecen categorías y marcas activas (más la que ya tenía el producto).
        # "Otros" y "Otra" van al final, para que la tienda primero busque la correcta.
        self.fields["categoria"].queryset = _otros_al_final(Categoria.objects.filter(
            Q(activa=True) | Q(pk=self.instance.categoria_id)
        ))
        self.fields["marca"].queryset = _otros_al_final(Marca.objects.filter(
            Q(activa=True) | Q(pk=self.instance.marca_id)
        ))
        self.fields["categoria"].empty_label = "Selecciona una categoría"
        self.fields["marca"].empty_label = "Selecciona una marca"
        # Lista con buscador (static/js/lista_buscable.js): se escribe el nombre o la inicial.
        self.fields["categoria"].widget.attrs["data-buscable"] = "Escribe la categoría…"
        self.fields["marca"].widget.attrs["data-buscable"] = "Escribe la marca o su inicial…"
        # Las fotos que se pueden quitar se dibujan aparte, con su miniatura (producto_form.html).
        self.fields["eliminar_fotos"].aparte = True
        # Precio de compra y de venta en una misma fila (ver _campos_formulario.html).
        # Lo mismo con la oferta y su fecha, y con el stock actual y el mínimo.
        for inicio, fin in (("categoria", "marca"), ("precio_compra", "precio"), ("precio_oferta", "oferta_hasta"),
                            ("stock", "stock_minimo")):
            self.fields[inicio].fila = "inicio"
            self.fields[fin].fila = "fin"
        if self.instance.pk:
            self.fields["version"].initial = self.instance.actualizado.isoformat()
            self.fields["eliminar_fotos"].queryset = self.instance.fotos.all()
            # Al editar, las fotos se manejan en la galería con un botón para cada cambio
            # (producto_form.html): cambiar o quitar la principal, hacer principal, reemplazar,
            # quitar y agregar. Todo se aplica al presionar "Guardar".
            for nombre in ("imagen", "fotos_nuevas"):
                self.fields[nombre].aparte = True
            for foto in self.instance.fotos.all():
                campo = forms.ImageField(
                    required=False,
                    validators=[FileExtensionValidator(allowed_extensions=EXTENSIONES_IMAGEN), validar_tamano_imagen],
                )
                campo.aparte = True
                self.fields[f"reemplazar_{foto.pk}"] = campo
            # Al editar se muestra el costo actual (si hubo ingresos, es el costo promedio).
            ficha = FichaInventario.objects.filter(producto=self.instance).first()
            self.fields["precio_compra"].initial = ficha.costo if ficha else None
            self.fields["stock_minimo"].initial = ficha.stock_minimo if ficha else 0
            self.fields["codigo"].initial = ficha.codigo if ficha else ""

    def clean(self):
        datos = super().clean()
        self._validar_oferta(datos)
        self._validar_destacado(datos)
        self._validar_cantidad_de_fotos(datos)
        self._validar_principal(datos)
        self._validar_version(datos)
        return datos

    def galeria(self):
        """Fotos adicionales con su campo de reemplazo, para dibujar la galería al editar."""
        if not self.instance.pk:
            return []
        return [{"foto": foto, "reemplazo": self[f"reemplazar_{foto.pk}"]} for foto in self.instance.fotos.all()]

    def fotos_libres(self):
        return MAX_FOTOS_EXTRA - (self.instance.fotos.count() if self.instance.pk else 0)

    def _validar_principal(self, datos):
        foto_id = datos.get("principal_foto")
        if not foto_id:
            return
        if not self.instance.pk or not self.instance.fotos.filter(pk=foto_id).exists():
            self.add_error(None, "La foto elegida como principal ya no existe. Vuelve a elegirla.")
        elif any(f.pk == foto_id for f in datos.get("eliminar_fotos") or []):
            self.add_error(None, "No puedes quitar la foto que elegiste como principal.")
        elif "imagen" in self.files or self.data.get(f"{self.add_prefix('imagen')}-clear"):
            self.add_error(None, "Elige solo un cambio para la foto principal: cambiarla, quitarla o usar una adicional.")

    def _validar_oferta(self, datos):
        precio, oferta, hasta = datos.get("precio"), datos.get("precio_oferta"), datos.get("oferta_hasta")
        if oferta is not None and precio is not None and oferta >= precio:
            self.add_error("precio_oferta", "El precio de oferta debe ser menor que el precio de venta.")
        if hasta and oferta is None:
            self.add_error("oferta_hasta", "Indica el precio de oferta o deja la fecha vacía.")
        # Solo se revisa si la tienda cambió la oferta: así una oferta vencida no impide editar lo demás.
        cambio = {"precio_oferta", "oferta_hasta"} & set(self.changed_data)
        if hasta and cambio and hasta < timezone.localdate():
            self.add_error("oferta_hasta", "La fecha de fin de la oferta no puede estar en el pasado.")

    def _validar_destacado(self, datos):
        if not datos.get("destacado"):
            return
        otros = Producto.objects.filter(tienda=self.tienda, destacado=True)
        if self.instance.pk:
            otros = otros.exclude(pk=self.instance.pk)
        if otros.count() >= MAX_DESTACADOS:
            self.add_error(
                "destacado",
                f"Ya tienes {MAX_DESTACADOS} productos destacados. Quita uno para destacar este.",
            )

    def _validar_cantidad_de_fotos(self, datos):
        nuevas = len(datos.get("fotos_nuevas") or [])
        actuales = self.instance.fotos.count() if self.instance.pk else 0
        quitadas = len(datos.get("eliminar_fotos") or [])
        if actuales - quitadas + nuevas > MAX_FOTOS_EXTRA:
            self.add_error(
                "fotos_nuevas",
                f"Puedes tener hasta {MAX_FOTOS_EXTRA} fotos adicionales "
                f"(ahora tienes {actuales - quitadas} y quieres agregar {nuevas}).",
            )

    def _validar_version(self, datos):
        version = datos.get("version")
        if self.instance.pk and version:
            actual = Producto.objects.filter(pk=self.instance.pk).first()
            if actual is None or actual.actualizado.isoformat() != version:
                # La próxima vez que guarde, ya sabiendo los datos actuales, se acepta.
                self.data = self.data.copy()
                self.data["version"] = actual.actualizado.isoformat() if actual else ""
                datos_actuales = (
                    f" Datos actuales: precio S/ {actual.precio}, stock {actual.stock}." if actual else ""
                )
                raise ValidationError(
                    "Este producto cambió mientras lo editabas (otra pestaña o una venta modificó sus datos)."
                    f"{datos_actuales} Corrige lo que necesites y vuelve a guardar."
                )

    def save(self, commit=True):
        producto = super().save(commit=commit)
        if commit:
            self.guardar_fotos(producto)
            self.guardar_ficha(producto)
        return producto

    def guardar_ficha(self, producto):
        """
        Guarda en la ficha de inventario el precio de compra y el stock mínimo, solo los que
        la tienda cambió: así no se pisa el costo promedio que calculó un ingreso.
        """
        cambios = {}
        if "precio_compra" in self.changed_data:
            cambios["costo"] = self.cleaned_data.get("precio_compra")
        if "stock_minimo" in self.changed_data:
            cambios["stock_minimo"] = self.cleaned_data.get("stock_minimo") or 0
        if "codigo" in self.changed_data:
            cambios["codigo"] = self.cleaned_data.get("codigo") or ""
        ficha = FichaInventario.objects.filter(producto=producto).first()
        if ficha is None:
            if not any(cambios.values()):
                return  # nada que guardar (vacío o 0)
            ficha = FichaInventario(producto=producto)
        if not cambios:
            return
        for campo, valor in cambios.items():
            setattr(ficha, campo, valor)
        ficha.save()

    def guardar_fotos(self, producto):
        quitadas = {foto.pk for foto in self.cleaned_data.get("eliminar_fotos") or []}
        for foto in self.cleaned_data.get("eliminar_fotos") or []:
            foto.delete()  # la señal borra también el archivo
        # Reemplazar una foto adicional: se guarda la nueva y se borra el archivo anterior.
        for foto in producto.fotos.exclude(pk__in=quitadas):
            archivo = self.cleaned_data.get(f"reemplazar_{foto.pk}")
            if archivo:
                borrar_archivo_al_confirmar(foto.imagen)
                foto.imagen = archivo
                foto.save()
        siguiente = (producto.fotos.aggregate(maximo=Max("orden"))["maximo"] or 0) + 1
        for posicion, archivo in enumerate(self.cleaned_data.get("fotos_nuevas") or []):
            FotoProducto.objects.create(producto=producto, imagen=archivo, orden=siguiente + posicion)
        self.hacer_principal(producto, self.cleaned_data.get("principal_foto"))

    def hacer_principal(self, producto, foto_id):
        """
        Intercambia la foto principal con una adicional. Se cambian solo los nombres de los
        archivos (update), sin volver a subirlos; al terminar, se ordenan sus carpetas.
        """
        foto = producto.fotos.filter(pk=foto_id).first() if foto_id else None
        if foto is None:
            return
        principal = Producto.objects.filter(pk=producto.pk).values_list("imagen", flat=True).first() or ""
        nombre_foto = foto.imagen.name
        Producto.objects.filter(pk=producto.pk).update(imagen=nombre_foto)
        if principal:
            FotoProducto.objects.filter(pk=foto.pk).update(imagen=principal)
        else:
            # No había foto principal: la adicional sube y deja de estar entre las adicionales.
            FotoProducto.objects.filter(pk=foto.pk).update(imagen="")
            FotoProducto.objects.get(pk=foto.pk).delete()  # sin archivo: no se borra nada
        producto.imagen.name = nombre_foto
        from .reubicar import reubicar_producto

        transaction.on_commit(lambda: reubicar_producto(producto.pk))

    def clean_codigo(self):
        """Regla: el código interno no se repite dentro de la misma tienda (sin importar mayúsculas)."""
        codigo = (self.cleaned_data.get("codigo") or "").strip()
        if codigo:
            repetido = FichaInventario.objects.filter(producto__tienda=self.tienda, codigo__iexact=codigo)
            if self.instance.pk:
                repetido = repetido.exclude(producto=self.instance)
            if repetido.exists():
                raise ValidationError("Ya tienes otro producto con este código.")
        return codigo

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split())
        if len(nombre) < 3:
            raise ValidationError("El nombre debe tener al menos 3 caracteres.")
        # Regla de negocio: una tienda no puede tener dos productos con el mismo nombre.
        repetidos = Producto.objects.filter(tienda=self.tienda, nombre__iexact=nombre)
        if self.instance.pk:
            repetidos = repetidos.exclude(pk=self.instance.pk)
        if repetidos.exists():
            raise ValidationError("Ya tienes un producto registrado con ese nombre.")
        return nombre


class BusquedaForm(EstiloBootstrapMixin, forms.Form):
    """CU-04 Buscar y filtrar productos."""

    ORDENES = [
        # Vacío = "Más relevantes": al buscar, primero lo que coincide en el nombre;
        # sin búsqueda, los más recientes.
        ("", "Más relevantes"),
        ("recientes", "Más recientes"),
        ("precio_asc", "Precio: menor a mayor"),
        ("precio_desc", "Precio: mayor a menor"),
        ("nombre", "Nombre (A-Z)"),
    ]

    q = forms.CharField(label="Buscar", required=False, max_length=100)
    categoria = forms.ModelChoiceField(
        label="Categoría", queryset=Categoria.objects.filter(activa=True), required=False, empty_label="Todas"
    )
    marca = forms.ModelChoiceField(
        label="Marca", queryset=Marca.objects.filter(activa=True), required=False, empty_label="Todas"
    )
    tienda = forms.ModelChoiceField(
        label="Tienda",
        queryset=Tienda.objects.filter(estado=Tienda.Estado.ACTIVA),
        required=False,
        empty_label="Todas",
    )
    precio_min = forms.DecimalField(label="Precio mín.", required=False, min_value=0, decimal_places=2)
    precio_max = forms.DecimalField(label="Precio máx.", required=False, min_value=0, decimal_places=2)
    orden = forms.ChoiceField(label="Ordenar por", choices=ORDENES, required=False)
    solo_ofertas = forms.BooleanField(label="Solo ofertas", required=False)

    def clean(self):
        datos = super().clean()
        minimo, maximo = datos.get("precio_min"), datos.get("precio_max")
        if minimo is not None and maximo is not None and minimo > maximo:
            raise ValidationError("El precio mínimo no puede ser mayor que el precio máximo.")
        return datos


class NombreUnicoForm(EstiloBootstrapMixin, forms.ModelForm):
    """Base para categorías y marcas (CU-07): el nombre no se repite, sin importar mayúsculas."""

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split())
        if len(nombre) < 2:
            raise ValidationError("El nombre debe tener al menos 2 caracteres.")
        repetidos = self._meta.model.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            repetidos = repetidos.exclude(pk=self.instance.pk)
        if repetidos.exists():
            raise ValidationError("Ya existe un registro con ese nombre.")
        return nombre


class CategoriaForm(NombreUnicoForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "activa"]
        help_texts = {"activa": "Si la desactivas, las tiendas ya no podrán elegirla en productos nuevos."}


class MarcaForm(NombreUnicoForm):
    class Meta:
        model = Marca
        fields = ["nombre", "activa"]
        help_texts = {"activa": "Si la desactivas, las tiendas ya no podrán elegirla en productos nuevos."}
