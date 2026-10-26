"""
Resumen y reportes del inventario de una tienda (Etapa 4).

Todo es privado de cada tienda: ganancias, costos y clientes no los ve nadie más.
Las ventas anuladas no cuentan en ningún reporte.

- Periodo: botones rápidos (hoy, 7 días, este mes, mes anterior, este año) o un
  rango "desde – hasta".
- Ganancia = (precio de venta − costo del momento de la venta) × cantidad. Las
  líneas vendidas sin costo conocido no se cuentan en la ganancia (se avisa cuántas).
- Sin movimiento: productos con stock que no se venden hace DIAS_SIN_MOVIMIENTO días.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Max, Q, Sum
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone

from catalogo.models import Producto

from .models import LineaVenta, Venta

DIAS_SIN_MOVIMIENTO = 60
MAX_DIAS_POR_DIA = 62  # rangos más largos se agrupan por mes en el gráfico

PERIODOS_RESUMEN = [
    ("hoy", "Hoy"), ("7dias", "Últimos 7 días"), ("mes", "Este mes"),
    ("mes_anterior", "Mes anterior"), ("anio", "Este año"),
]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"]
DINERO = DecimalField(max_digits=14, decimal_places=2)


@dataclass
class Rango:
    desde: date
    hasta: date
    clave: str      # botón elegido, o "" si es un rango a mano
    etiqueta: str

    @property
    def dias(self):
        return (self.hasta - self.desde).days + 1

    def inicio(self):
        return timezone.make_aware(datetime.combine(self.desde, time.min))

    def fin(self):
        return timezone.make_aware(datetime.combine(self.hasta + timedelta(days=1), time.min))


def _fecha(texto):
    try:
        return date.fromisoformat(texto)
    except (TypeError, ValueError):
        return None


def rango_desde_get(get):
    """Lee el periodo de la URL. Devuelve (rango, error)."""
    hoy = timezone.localdate()
    desde, hasta = _fecha(get.get("desde")), _fecha(get.get("hasta"))
    if desde or hasta:
        desde, hasta = desde or hasta, hasta or desde
        if desde > hasta:
            return rango_desde_get({})[0], "La fecha «desde» no puede ser posterior a «hasta»."
        if hasta > hoy:
            hasta = hoy
        return Rango(desde, hasta, "", f"Del {desde:%d/%m/%Y} al {hasta:%d/%m/%Y}"), None
    clave = get.get("periodo", "mes")
    inicio_mes = hoy.replace(day=1)
    fin_mes_anterior = inicio_mes - timedelta(days=1)
    opciones = {
        "hoy": (hoy, hoy),
        "7dias": (hoy - timedelta(days=6), hoy),
        "mes": (inicio_mes, hoy),
        "mes_anterior": (fin_mes_anterior.replace(day=1), fin_mes_anterior),
        "anio": (hoy.replace(month=1, day=1), hoy),
    }
    if clave not in opciones:
        clave = "mes"
    desde, hasta = opciones[clave]
    return Rango(desde, hasta, clave, dict(PERIODOS_RESUMEN)[clave]), None


def ventas_validas(tienda, rango):
    return Venta.objects.filter(tienda=tienda, anulada=False, fecha__gte=rango.inicio(), fecha__lt=rango.fin())


def _ganancia_de(lineas):
    """Ganancia de las líneas con costo conocido y cuántas no lo tienen."""
    con_costo = lineas.filter(costo_unitario__isnull=False)
    ganancia = con_costo.aggregate(
        g=Sum(ExpressionWrapper((F("precio_unitario") - F("costo_unitario")) * F("cantidad"), output_field=DINERO))
    )["g"] or Decimal("0")
    vendido_con_costo = con_costo.aggregate(
        v=Sum(ExpressionWrapper(F("precio_unitario") * F("cantidad"), output_field=DINERO))
    )["v"] or Decimal("0")
    return ganancia, vendido_con_costo, lineas.filter(costo_unitario__isnull=True).count()


def resumen_ventas(tienda, rango):
    ventas = ventas_validas(tienda, rango)
    totales = ventas.aggregate(total=Coalesce(Sum("total"), Decimal("0"), output_field=DINERO), cantidad=Count("id"))
    lineas = LineaVenta.objects.filter(venta__in=ventas)
    totales["unidades"] = lineas.aggregate(u=Sum("cantidad"))["u"] or 0
    totales["ticket"] = (totales["total"] / totales["cantidad"]).quantize(Decimal("0.01")) if totales["cantidad"] else Decimal("0")
    ganancia, vendido_con_costo, sin_costo = _ganancia_de(lineas)
    totales["ganancia"] = ganancia
    totales["lineas_sin_costo"] = sin_costo
    totales["margen"] = round(ganancia * 100 / vendido_con_costo, 1) if vendido_con_costo else None
    totales["anuladas"] = Venta.objects.filter(
        tienda=tienda, anulada=True, fecha__gte=rango.inicio(), fecha__lt=rango.fin()
    ).count()
    return totales


def ventas_en_el_tiempo(tienda, rango):
    """Serie para el gráfico: total vendido y ganancia por día (o por mes si el rango es largo)."""
    por_mes = rango.dias > MAX_DIAS_POR_DIA
    trunc = TruncMonth("venta__fecha") if por_mes else TruncDate("venta__fecha")
    filas = (
        LineaVenta.objects.filter(venta__in=ventas_validas(tienda, rango))
        .annotate(periodo=trunc).values("periodo")
        .annotate(
            vendido=Sum(ExpressionWrapper(F("precio_unitario") * F("cantidad"), output_field=DINERO)),
            ganancia=Sum(
                ExpressionWrapper((F("precio_unitario") - F("costo_unitario")) * F("cantidad"), output_field=DINERO),
                filter=Q(costo_unitario__isnull=False),
            ),
        ).order_by("periodo")
    )
    datos = {}
    for fila in filas:
        clave = fila["periodo"]
        if isinstance(clave, datetime):
            clave = timezone.localtime(clave).date() if timezone.is_aware(clave) else clave.date()
        if por_mes:
            clave = clave.replace(day=1)
        datos[clave] = (fila["vendido"] or Decimal("0"), fila["ganancia"] or Decimal("0"))

    etiquetas, vendido, ganancia = [], [], []
    actual = rango.desde.replace(day=1) if por_mes else rango.desde
    while actual <= rango.hasta:
        v, g = datos.get(actual, (Decimal("0"), Decimal("0")))
        etiquetas.append(f"{MESES[actual.month - 1]} {actual:%Y}" if por_mes else f"{actual:%d/%m}")
        vendido.append(float(v))
        ganancia.append(float(g))
        if por_mes:
            actual = (actual.replace(day=28) + timedelta(days=4)).replace(day=1)
        else:
            actual += timedelta(days=1)
    return {"etiquetas": etiquetas, "vendido": vendido, "ganancia": ganancia, "por_mes": por_mes}


def por_metodo_de_pago(tienda, rango):
    filas = ventas_validas(tienda, rango).order_by().values("metodo_pago").annotate(
        suma=Sum("total"), cantidad=Count("id")
    ).order_by("-suma")
    return [
        {"metodo": Venta.MetodoPago(f["metodo_pago"]).label, "suma": f["suma"], "cantidad": f["cantidad"]}
        for f in filas
    ]


def mas_vendidos(tienda, rango, limite=10):
    lineas = LineaVenta.objects.filter(venta__in=ventas_validas(tienda, rango))
    filas = (
        lineas.values("producto_id", "producto_nombre")
        .annotate(
            unidades=Sum("cantidad"),
            vendido=Sum(ExpressionWrapper(F("precio_unitario") * F("cantidad"), output_field=DINERO)),
            ganancia=Sum(
                ExpressionWrapper((F("precio_unitario") - F("costo_unitario")) * F("cantidad"), output_field=DINERO),
                filter=Q(costo_unitario__isnull=False),
            ),
        )
        .order_by("-unidades", "-vendido")
    )
    return list(filas[:limite]) if limite else list(filas)


def inventario_valorizado(tienda):
    productos = (
        Producto.objects.filter(tienda=tienda, stock__gt=0)
        .select_related("categoria")
        .annotate(
            costo=F("ficha__costo"),
            valor_costo=ExpressionWrapper(F("stock") * F("ficha__costo"), output_field=DINERO),
            valor_venta=ExpressionWrapper(F("stock") * F("precio"), output_field=DINERO),
        )
        .order_by("-valor_costo", "nombre")
    )
    # Los totales se calculan sobre la consulta sin anotaciones: sumar una anotación
    # que usa la ficha (un JOIN) daba 0 en SQLite.
    totales = Producto.objects.filter(tienda=tienda, stock__gt=0).aggregate(
        unidades=Coalesce(Sum("stock"), 0),
        valor_costo=Sum(ExpressionWrapper(F("stock") * F("ficha__costo"), output_field=DINERO)),
        valor_venta=Sum(ExpressionWrapper(F("stock") * F("precio"), output_field=DINERO)),
        sin_costo=Count("id", filter=Q(ficha__costo__isnull=True)),
    )
    totales["valor_costo"] = totales["valor_costo"] or Decimal("0")
    totales["valor_venta"] = totales["valor_venta"] or Decimal("0")
    return productos, totales


def sin_movimiento(tienda, dias=DIAS_SIN_MOVIMIENTO):
    """
    Productos con stock que no se venden hace `dias` días (o nunca se vendieron).
    Los productos creados hace menos de `dias` días no se cuentan: aún son nuevos.
    """
    limite = timezone.now() - timedelta(days=dias)
    productos = (
        Producto.objects.filter(tienda=tienda, stock__gt=0, creado__lte=limite)
        .annotate(
            ultima_venta=Max("lineas_venta__venta__fecha", filter=Q(lineas_venta__venta__anulada=False)),
            costo=F("ficha__costo"),
        )
        .filter(Q(ultima_venta__isnull=True) | Q(ultima_venta__lte=limite))
        .order_by("ultima_venta", "creado")
    )
    ahora = timezone.now()
    resultado = []
    for p in productos:
        desde = p.ultima_venta or p.creado
        p.dias_sin_vender = (ahora - desde).days
        p.valor_costo = p.stock * p.costo if p.costo is not None else None
        resultado.append(p)
    return resultado


def filtro_stock_bajo():
    return Q(stock__gt=0, ficha__stock_minimo__gt=0, stock__lte=F("ficha__stock_minimo"))


def alertas_de_stock(tienda):
    """Productos agotados o con stock bajo (stock ≤ stock mínimo de su ficha)."""
    return (
        Producto.objects.filter(tienda=tienda)
        .filter(Q(stock=0) | filtro_stock_bajo())
        .annotate(stock_minimo=Coalesce("ficha__stock_minimo", 0))
        .order_by("stock", "nombre")
    )


def cantidad_de_alertas(tienda):
    return Producto.objects.filter(tienda=tienda).filter(Q(stock=0) | filtro_stock_bajo()).count()
