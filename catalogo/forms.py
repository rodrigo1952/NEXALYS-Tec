from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db.models import Max, Q
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

    # Precio de compra: dato PRIVADO de la tienda (es el "costo" de la ficha de inventario).
    # No es un campo de Producto: se guarda en la ficha. Se edita aquí o en la ficha; es el mismo dato.
    precio_compra = forms.DecimalField(
        label="Precio de compra (S/)", required=False, min_value=Decimal("0"), max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        help_text="Opcional. Solo tú lo ves; sirve para calcular tu ganancia.",
    )

    field_order = [
        "nombre", "categoria", "marca", "precio_compra", "precio", "precio_oferta", "oferta_hasta",
        "stock", "descripcion", "imagen", "fotos_nuevas", "activo", "destacado",
    ]

    class Meta:
        model = Producto
        fields = [
            "nombre", "categoria", "marca", "precio", "precio_oferta", "oferta_hasta",
            "stock", "descripcion", "imagen", "activo", "destacado",
        ]
        labels = {"imagen": "Foto principal", "precio": "Precio de venta (S/)"}
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
        self.fields["categoria"].queryset = Categoria.objects.filter(
            Q(activa=True) | Q(pk=self.instance.categoria_id)
        )
        self.fields["marca"].queryset = Marca.objects.filter(
            Q(activa=True) | Q(pk=self.instance.marca_id)
        )
        self.fields["categoria"].empty_label = "Selecciona una categoría"
        self.fields["marca"].empty_label = "Selecciona una marca"
        # Las fotos que se pueden quitar se dibujan aparte, con su miniatura (producto_form.html).
        self.fields["eliminar_fotos"].aparte = True
        # Precio de compra y de venta en una misma fila (ver _campos_formulario.html).
        self.fields["precio_compra"].fila = "inicio"
        self.fields["precio"].fila = "fin"
        if self.instance.pk:
            self.fields["version"].initial = self.instance.actualizado.isoformat()
            self.fields["eliminar_fotos"].queryset = self.instance.fotos.all()
            # Al editar se muestra el costo actual (si hubo ingresos, es el costo promedio).
            ficha = FichaInventario.objects.filter(producto=self.instance).first()
            self.fields["precio_compra"].initial = ficha.costo if ficha else None

    def clean(self):
        datos = super().clean()
        self._validar_oferta(datos)
        self._validar_destacado(datos)
        self._validar_cantidad_de_fotos(datos)
        self._validar_version(datos)
        return datos

    def _validar_oferta(self, datos):
        precio, oferta, hasta = datos.get("precio"), datos.get("precio_oferta"), datos.get("oferta_hasta")
        if oferta is not None and precio is not None and oferta >= precio:
            self.add_error("precio_oferta", "El precio de oferta debe ser menor que el precio normal.")
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
            self.guardar_precio_compra(producto)
        return producto

    def guardar_precio_compra(self, producto):
        """Solo si la tienda lo cambió: así no se pisa el costo promedio que calculó un ingreso."""
        if "precio_compra" not in self.changed_data:
            return
        costo = self.cleaned_data.get("precio_compra")
        ficha = FichaInventario.objects.filter(producto=producto).first()
        if ficha is None:
            if costo is None:
                return
            ficha = FichaInventario(producto=producto)
        ficha.costo = costo
        ficha.save()

    def guardar_fotos(self, producto):
        for foto in self.cleaned_data.get("eliminar_fotos") or []:
            foto.delete()  # la señal borra también el archivo
        siguiente = (producto.fotos.aggregate(maximo=Max("orden"))["maximo"] or 0) + 1
        for posicion, archivo in enumerate(self.cleaned_data.get("fotos_nuevas") or []):
            FotoProducto.objects.create(producto=producto, imagen=archivo, orden=siguiente + posicion)

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
