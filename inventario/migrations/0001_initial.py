import decimal

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

NO_NEGATIVO = django.core.validators.MinValueValidator(decimal.Decimal("0"), message="No puede ser negativo.")
SET_NULL = django.db.models.deletion.SET_NULL
CASCADE = django.db.models.deletion.CASCADE


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("catalogo", "0008_imagenes_por_tienda"),
        ("tiendas", "0006_suspendida_en"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FichaInventario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("costo", models.DecimalField(
                    blank=True, decimal_places=2, max_digits=10, null=True, validators=[NO_NEGATIVO],
                    help_text="Cuánto te cuesta cada unidad. Sirve para calcular tu ganancia y el valor de tu inventario.",
                    verbose_name="costo de compra (S/)",
                )),
                ("stock_minimo", models.PositiveIntegerField(
                    default=0, help_text="Te avisaremos cuando el stock llegue a esta cantidad. 0 = sin aviso.",
                    verbose_name="stock mínimo",
                )),
                ("codigo", models.CharField(
                    blank=True, help_text="Opcional. El código que usas en tu tienda (SKU).", max_length=40,
                    verbose_name="código interno",
                )),
                ("actualizado", models.DateTimeField(auto_now=True, verbose_name="actualizado")),
                ("producto", models.OneToOneField(
                    on_delete=CASCADE, related_name="ficha", to="catalogo.producto", verbose_name="producto",
                )),
            ],
            options={"verbose_name": "ficha de inventario", "verbose_name_plural": "fichas de inventario"},
        ),
        migrations.CreateModel(
            name="Proveedor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=120, verbose_name="nombre o razón social")),
                ("ruc", models.CharField(
                    blank=True, max_length=11, verbose_name="RUC",
                    validators=[django.core.validators.RegexValidator("^\\d{11}$", "El RUC tiene 11 dígitos.")],
                )),
                ("telefono", models.CharField(
                    blank=True, max_length=15, verbose_name="teléfono",
                    validators=[django.core.validators.RegexValidator("^[\\d +-]{6,15}$", "Escribe solo números (6 a 15 dígitos).")],
                )),
                ("correo", models.EmailField(blank=True, max_length=254, verbose_name="correo")),
                ("notas", models.TextField(blank=True, verbose_name="notas")),
                ("creado", models.DateTimeField(auto_now_add=True, verbose_name="registrado")),
                ("tienda", models.ForeignKey(
                    on_delete=CASCADE, related_name="proveedores", to="tiendas.tienda", verbose_name="tienda",
                )),
            ],
            options={
                "verbose_name": "proveedor", "verbose_name_plural": "proveedores", "ordering": ["nombre"],
                "constraints": [models.UniqueConstraint(fields=("tienda", "nombre"), name="proveedor_unico_por_tienda")],
            },
        ),
        migrations.CreateModel(
            name="Venta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tienda_nombre", models.CharField(max_length=100, verbose_name="tienda (nombre)")),
                ("numero", models.PositiveIntegerField(verbose_name="número de venta")),
                ("fecha", models.DateTimeField(db_index=True, default=django.utils.timezone.now, verbose_name="fecha")),
                ("metodo_pago", models.CharField(
                    choices=[("efectivo", "Efectivo"), ("yape_plin", "Yape / Plin"), ("tarjeta", "Tarjeta"),
                             ("transferencia", "Transferencia"), ("otro", "Otro")],
                    default="efectivo", max_length=15, verbose_name="método de pago",
                )),
                ("cliente_nombre", models.CharField(blank=True, max_length=120, verbose_name="cliente")),
                ("cliente_documento", models.CharField(blank=True, max_length=11, verbose_name="DNI o RUC del cliente")),
                ("total", models.DecimalField(decimal_places=2, default=decimal.Decimal("0"), max_digits=10, verbose_name="total (S/)")),
                ("nota", models.CharField(blank=True, max_length=255, verbose_name="nota")),
                ("origen", models.CharField(blank=True, max_length=60, verbose_name="origen")),
                ("anulada", models.BooleanField(default=False, verbose_name="anulada")),
                ("motivo_anulacion", models.CharField(blank=True, max_length=255, verbose_name="motivo de la anulación")),
                ("anulada_en", models.DateTimeField(blank=True, null=True, verbose_name="anulada el")),
                ("tienda", models.ForeignKey(
                    blank=True, null=True, on_delete=SET_NULL, related_name="ventas", to="tiendas.tienda", verbose_name="tienda",
                )),
                ("usuario", models.ForeignKey(
                    blank=True, null=True, on_delete=SET_NULL, related_name="ventas_registradas",
                    to=settings.AUTH_USER_MODEL, verbose_name="registrada por",
                )),
            ],
            options={
                "verbose_name": "venta", "verbose_name_plural": "ventas", "ordering": ["-fecha", "-id"],
                "constraints": [models.UniqueConstraint(fields=("tienda", "numero"), name="numero_de_venta_unico_por_tienda")],
            },
        ),
        migrations.CreateModel(
            name="LineaVenta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("producto_nombre", models.CharField(max_length=200, verbose_name="producto (nombre)")),
                ("cantidad", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)], verbose_name="cantidad")),
                ("precio_unitario", models.DecimalField(decimal_places=2, max_digits=10, validators=[NO_NEGATIVO], verbose_name="precio unitario (S/)")),
                ("costo_unitario", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="costo unitario (S/)")),
                ("producto", models.ForeignKey(
                    blank=True, null=True, on_delete=SET_NULL, related_name="lineas_venta", to="catalogo.producto",
                )),
                ("venta", models.ForeignKey(on_delete=CASCADE, related_name="lineas", to="inventario.venta", verbose_name="venta")),
            ],
            options={"verbose_name": "línea de venta", "verbose_name_plural": "líneas de venta"},
        ),
        migrations.CreateModel(
            name="Ingreso",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("proveedor_nombre", models.CharField(blank=True, max_length=120, verbose_name="proveedor (nombre)")),
                ("documento", models.CharField(blank=True, max_length=40, verbose_name="factura o guía del proveedor")),
                ("fecha", models.DateTimeField(db_index=True, default=django.utils.timezone.now, verbose_name="fecha")),
                ("total", models.DecimalField(decimal_places=2, default=decimal.Decimal("0"), max_digits=10, verbose_name="total (S/)")),
                ("nota", models.CharField(blank=True, max_length=255, verbose_name="nota")),
                ("proveedor", models.ForeignKey(
                    blank=True, null=True, on_delete=SET_NULL, related_name="ingresos", to="inventario.proveedor", verbose_name="proveedor",
                )),
                ("tienda", models.ForeignKey(on_delete=CASCADE, related_name="ingresos", to="tiendas.tienda", verbose_name="tienda")),
                ("usuario", models.ForeignKey(
                    blank=True, null=True, on_delete=SET_NULL, related_name="ingresos_registrados",
                    to=settings.AUTH_USER_MODEL, verbose_name="registrado por",
                )),
            ],
            options={"verbose_name": "ingreso de mercadería", "verbose_name_plural": "ingresos de mercadería", "ordering": ["-fecha", "-id"]},
        ),
        migrations.CreateModel(
            name="LineaIngreso",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("producto_nombre", models.CharField(max_length=200, verbose_name="producto (nombre)")),
                ("cantidad", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)], verbose_name="cantidad")),
                ("costo_unitario", models.DecimalField(decimal_places=2, max_digits=10, validators=[NO_NEGATIVO], verbose_name="costo unitario (S/)")),
                ("ingreso", models.ForeignKey(on_delete=CASCADE, related_name="lineas", to="inventario.ingreso", verbose_name="ingreso")),
                ("producto", models.ForeignKey(
                    blank=True, null=True, on_delete=SET_NULL, related_name="lineas_ingreso", to="catalogo.producto",
                )),
            ],
            options={"verbose_name": "línea de ingreso", "verbose_name_plural": "líneas de ingreso"},
        ),
        migrations.CreateModel(
            name="Movimiento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tienda_nombre", models.CharField(max_length=100, verbose_name="tienda (nombre)")),
                ("producto_nombre", models.CharField(max_length=200, verbose_name="producto (nombre)")),
                ("tipo", models.CharField(
                    choices=[("inicial", "Inventario inicial"), ("venta", "Venta"), ("anulacion", "Venta anulada"),
                             ("ingreso", "Ingreso de mercadería"), ("ajuste", "Ajuste"), ("conteo", "Conteo físico"),
                             ("edicion", "Cambio al editar el producto")],
                    max_length=10, verbose_name="tipo",
                )),
                ("motivo", models.CharField(
                    blank=True,
                    choices=[("dano", "Producto dañado"), ("perdida", "Pérdida o robo"),
                             ("devolucion", "Devolución de un cliente"), ("otro", "Otro")],
                    max_length=12, verbose_name="motivo",
                )),
                ("cantidad", models.IntegerField(verbose_name="cantidad")),
                ("stock_resultante", models.PositiveIntegerField(verbose_name="stock después")),
                ("nota", models.CharField(blank=True, max_length=255, verbose_name="nota")),
                ("fecha", models.DateTimeField(db_index=True, default=django.utils.timezone.now, verbose_name="fecha")),
                ("ingreso", models.ForeignKey(
                    blank=True, null=True, on_delete=SET_NULL, related_name="movimientos", to="inventario.ingreso",
                )),
                ("producto", models.ForeignKey(
                    blank=True, null=True, on_delete=SET_NULL, related_name="movimientos", to="catalogo.producto", verbose_name="producto",
                )),
                ("tienda", models.ForeignKey(
                    blank=True, null=True, on_delete=SET_NULL, related_name="movimientos", to="tiendas.tienda", verbose_name="tienda",
                )),
                ("usuario", models.ForeignKey(
                    blank=True, null=True, on_delete=SET_NULL, related_name="movimientos_inventario",
                    to=settings.AUTH_USER_MODEL, verbose_name="registrado por",
                )),
                ("venta", models.ForeignKey(
                    blank=True, null=True, on_delete=SET_NULL, related_name="movimientos", to="inventario.venta",
                )),
            ],
            options={
                "verbose_name": "movimiento de inventario",
                "verbose_name_plural": "movimientos de inventario (kardex)",
                "ordering": ["-fecha", "-id"],
                "indexes": [
                    models.Index(fields=["tienda", "fecha"], name="movimiento_tienda_fecha"),
                    models.Index(fields=["producto", "fecha"], name="movimiento_producto_fecha"),
                ],
            },
        ),
    ]
