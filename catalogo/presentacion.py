"""
Productos de presentación: 3 tiendas de demostración con productos reales para mostrar
NEXALYS Tec en la exposición del proyecto.

    python manage.py cargar_productos_presentacion

- Los modelos y precios son reales: se tomaron de Falabella.com.pe (vendedores de su
  marketplace) el 28 de octubre de 2026. En las ofertas, "precio" es el precio tachado y
  "oferta" el precio rebajado que mostraba la página.
- Las tiendas son FICTICIAS (nombres inventados en Quillabamba) y sus WhatsApp son
  números del equipo.
- El stock y el precio de compra (costo) son de demostración: el costo no es público, así
  que se estima entre el 70 % y el 80 % del precio de venta.
- Para la demostración de las alertas, cada tienda tiene 3 productos SIN precio de compra,
  3 con stock bajo y 1 agotado.
- Los productos se cargan sin imagen. El campo "enlace" dice dónde ver la foto de cada uno.

Se puede ejecutar varias veces: lo que ya existe (misma tienda, mismo nombre de producto)
no se toca ni se duplica.
"""

from datetime import date, time
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import quote_plus

from django.contrib.auth.models import Group, User
from django.db import transaction
from django.utils import timezone

from inventario.models import FichaInventario
from tiendas.models import HorarioDia, Tienda

from .demo import CLAVE_DEMO, correo_demo
from .models import Categoria, Marca, Producto

# El costo de demostración varía entre el 70 % y el 80 % del precio que paga el cliente.
PORCENTAJES_COSTO = [Decimal("0.75"), Decimal("0.70"), Decimal("0.78"), Decimal("0.72"), Decimal("0.80")]
STOCK_MINIMO = 3
FUENTE = "Falabella.com.pe, 28-oct-2026"


def buscar_en_falabella(texto):
    return "https://www.falabella.com.pe/falabella-pe/search?Ntt=" + quote_plus(texto)


def falabella(ruta):
    return "https://www.falabella.com.pe/falabella-pe/" + ruta


def horario(lunes_a_viernes, sabado, domingo=None):
    """Cada tramo es (abre, cierra, inicio_refrigerio, fin_refrigerio) o None si cierra."""
    return [lunes_a_viernes] * 5 + [sabado, domingo]


TIENDAS = [
    {
        "usuario": "selvabyte",
        "nombres": "Tienda",
        "apellidos": "Selva Byte",
        "nombre": "Selva Byte",
        "direccion": "Jr. Libertad, Quillabamba",
        "whatsapp": "930909090",
        "descripcion": (
            "Tienda de demostración de NEXALYS Tec. Celulares, audio, tablets, smartwatches y consolas "
            "en Quillabamba."
        ),
        "horario": horario(
            (time(9), time(20), time(13), time(15)),
            (time(9), time(20), time(13), time(15)),
            (time(9), time(13), None, None),
        ),
    },
    {
        "usuario": "valledigital",
        "nombres": "Tienda",
        "apellidos": "Valle Digital Tech",
        "nombre": "Valle Digital Tech",
        "direccion": "Av. Martín Pío Concha, Quillabamba",
        "whatsapp": "920909090",
        "descripcion": (
            "Tienda de demostración de NEXALYS Tec. Laptops, computadoras, monitores, televisores y "
            "accesorios de cómputo."
        ),
        "horario": horario(
            (time(8, 30), time(20, 30), time(13), time(15)),
            (time(8, 30), time(20, 30), time(13), time(15)),
        ),
    },
    {
        "usuario": "kantutech",
        "nombres": "Tienda",
        "apellidos": "Kantu Tech",
        "nombre": "Kantu Tech",
        "direccion": "Jr. Espinar, Quillabamba",
        "whatsapp": "910909090",
        "descripcion": (
            "Tienda de demostración de NEXALYS Tec. Impresoras y tintas, cámaras de seguridad, "
            "repuestos de PC, redes y UPS."
        ),
        "horario": horario(
            (time(9), time(19), None, None),
            (time(9), time(13), None, None),
        ),
    },
]


def p(tienda, categoria, marca, nombre, precio, *, oferta=None, hasta=None, stock=8, alerta="",
      destacado=False, descripcion="", enlace=None):
    """
    alerta: "" normal · "sin_costo" sin precio de compra · "bajo" stock bajo · "agotado" stock 0.
    """
    return {
        "tienda": tienda, "categoria": categoria, "marca": marca, "nombre": nombre,
        "precio": Decimal(precio), "oferta": Decimal(oferta) if oferta else None, "hasta": hasta,
        "stock": stock, "alerta": alerta, "destacado": destacado, "descripcion": descripcion,
        "enlace": enlace or buscar_en_falabella(nombre),
    }


SB, VD, KT = "Selva Byte", "Valle Digital Tech", "Kantu Tech"

PRODUCTOS = [
    # --- Selva Byte: celulares, audio, tablets y gadgets -------------------------------------
    p(SB, "Celulares", "Samsung", "Samsung Galaxy A26 5G 128GB 6GB RAM Negro", "1199", stock=9, destacado=True,
      descripcion="Pantalla 6.7\", 5G, cámara principal de 50 MP, 6 GB de RAM y 128 GB de almacenamiento.",
      enlace=falabella("product/149397537/Celular-Samsung-Galaxy-A26-5G-Negro-128GB-6GB-RAM/149397539")),
    p(SB, "Celulares", "Xiaomi", "Xiaomi Redmi Note 14 4G 256GB 8GB RAM Azul", "949", stock=7, destacado=True,
      descripcion="Pantalla AMOLED 6.67\", 8 GB de RAM, 256 GB de almacenamiento, versión 4G.",
      enlace=falabella("product/139995405/Xiaomi-Redmi-Note-14-4G-8+256GB-Azul-24117RN76L/139995408")),
    p(SB, "Celulares", "Honor", "Honor X7c 256GB 8GB RAM Midnight Black", "999", oferta="839", stock=6,
      descripcion="Pantalla 6.77\", 8 GB de RAM, 256 GB de almacenamiento, MagicOS 8.0.",
      enlace=falabella("product/140815350/Celular-Honor-X7C-ALT-LX3-8GB-256GB-Midnight-Black-5109BNCS/140815351")),
    p(SB, "Celulares", "Motorola", "Motorola Moto G77 256GB 8GB RAM Negro", "1049", stock=2, alerta="bajo",
      descripcion="Cámara de 108 MP, 8 GB de RAM y 256 GB de almacenamiento."),
    p(SB, "Celulares", "Infinix", "Infinix Hot 60 Pro 256GB 8GB RAM Negro", "809", stock=8, alerta="sin_costo",
      descripcion="Modelo X6885, 8 GB de RAM (+8 GB virtuales) y 256 GB de almacenamiento."),
    p(SB, "Audio", "Sony", "Audífonos Sony WH-CH520 Bluetooth 50 h Negro", "250", oferta="199.99",
      hasta=date(2026, 12, 31), stock=10,
      descripcion="Audífonos on-ear inalámbricos con micrófono y hasta 50 horas de batería.",
      enlace=falabella("product/121498947/Audifonos-Bluetooth-Sony-WH-CH520-50h-Negro/121498949")),
    p(SB, "Audio", "JBL", "Audífonos JBL Tune 780NC Bluetooth Over-Ear", "279", stock=0, alerta="agotado",
      descripcion="Audífonos over-ear inalámbricos con cancelación activa de ruido y sonido JBL Pure Bass."),
    p(SB, "Audio", "Xiaomi", "Audífonos Redmi Buds 6 Active Bluetooth Negro", "109", stock=12,
      descripcion="Audífonos in-ear true wireless con estuche de carga.",
      enlace=falabella("product/132796621/Audifonos-Bluetooth-Xiaomi-Redmi-Buds-6-Active-Negro/132796622")),
    p(SB, "Audio", "Soundcore (Anker)", "Audífonos Soundcore Q20i Bluetooth ANC Negro", "130.90", stock=6,
      alerta="sin_costo", descripcion="Audífonos over-ear con cancelación activa de ruido y audio Hi-Res.",
      enlace=falabella("category/cat800582/Audifonos?f.product.brandName=soundcore")),
    p(SB, "Audio", "HyperX", "Audífonos Gamer HyperX Cloud Stinger 2", "179", stock=1, alerta="bajo",
      descripcion="Audífonos gamer alámbricos con micrófono, para PC y consolas.",
      enlace=falabella("shop/hyperx-cloud-stinger")),
    p(SB, "Otros", "Nintendo", "Consola Nintendo Switch 2", "2299", stock=4, destacado=True,
      descripcion="Consola híbrida de Nintendo: se juega en el televisor o en modo portátil.",
      enlace=falabella("product/145400594/Consola-Nintendo-Switch-2/145400595")),
    p(SB, "Otros", "Xiaomi", "Smartwatch Redmi Watch 5 Active", "129", stock=9,
      descripcion="Reloj inteligente con pantalla grande, llamadas Bluetooth y modos deportivos."),
    p(SB, "Otros", "Amazfit", "Smartwatch Amazfit Bip U Pro GPS Negro", "269", stock=5, alerta="sin_costo",
      descripcion="Smartwatch con GPS, medición de SpO2 y resistencia al agua 5 ATM."),
    p(SB, "Tablets", "Xiaomi", "Tablet Xiaomi Redmi Pad 2 9.7\" Gris", "499", stock=2, alerta="bajo",
      descripcion="Tablet de 9.7 pulgadas, ideal para clases, lectura y videos."),
    p(SB, "Tablets", "Samsung", "Tablet Samsung Galaxy Tab S10 Lite 10.9\" 6GB 128GB", "1399", stock=5,
      descripcion="Pantalla de 10.9\", 6 GB de RAM y 128 GB de almacenamiento."),

    # --- Valle Digital Tech: cómputo -----------------------------------------------------------
    p(VD, "Laptops", "Lenovo", "Laptop Lenovo IdeaPad Slim 3 15.6\" Ryzen 5 7520U 8GB 512GB SSD", "2099", stock=6,
      destacado=True, descripcion="Pantalla Full HD de 15.6\", AMD Ryzen 5 7520U, 8 GB de RAM y SSD de 512 GB."),
    p(VD, "Laptops", "Acer", "Laptop Acer Aspire Go 15.6\" Intel Core Ultra 5 115U 16GB 1TB SSD", "2749", stock=4,
      alerta="sin_costo", descripcion="Intel Core Ultra 5 115U, 16 GB de RAM y SSD de 1 TB."),
    p(VD, "Pantallas", "Samsung", "Monitor Samsung Odyssey G3 24\" FHD 180Hz LS24DG300", "425", stock=7,
      descripcion="Monitor gamer de 24\", panel VA Full HD, 180 Hz y 1 ms."),
    p(VD, "Pantallas", "LG", "Monitor LG UltraGear 24GS50F-B 24\" FHD 180Hz", "479.50", stock=5, destacado=True,
      descripcion="Monitor gamer de 24\", panel VA Full HD, 180 Hz, 1 ms, HDR10 y FreeSync."),
    p(VD, "Pantallas", "Teros", "Monitor Teros TE-2417S 23.8\" IPS 144Hz", "489", oferta="299", stock=8,
      descripcion="Monitor de 23.8\" IPS Full HD a 144 Hz, con HDMI y DisplayPort."),
    p(VD, "Pantallas", "Hisense", "Televisor Hisense 43\" Hi-QLED 4K 43QD5SV Smart TV", "899", stock=2,
      alerta="bajo", descripcion="Smart TV de 43 pulgadas con resolución 4K UHD y tecnología Hi-QLED."),
    p(VD, "Computadoras de escritorio", "HP", "All in One HP OmniStudio 24-cv0051la Ryzen 5 8GB 512GB 23.8\" Táctil",
      "3899", oferta="3249", stock=3,
      descripcion="Pantalla táctil Full HD de 23.8\", AMD Ryzen 5, 8 GB de RAM, SSD de 512 GB y Windows 11 Home."),
    p(VD, "Computadoras de escritorio", "Lenovo", "All in One Lenovo IdeaCentre Core i5 8GB 512GB 23.8\" 100Hz",
      "2849", stock=4, descripcion="Intel Core i5, 8 GB de RAM, SSD de 512 GB y pantalla Full HD de 100 Hz."),
    p(VD, "Computadoras de escritorio", "Apple", "Apple iMac 24\" Chip M4 16GB 256GB", "6299", stock=2,
      alerta="bajo", destacado=True, descripcion="iMac con chip M4, pantalla Retina 4.5K, 16 GB de RAM y 256 GB."),
    p(VD, "Computadoras de escritorio", "Asus", "All in One ASUS P440VAK Core 5 210H 8GB 512GB 23.8\"", "2959",
      stock=3, alerta="sin_costo", descripcion="Intel Core 5 210H, 8 GB de RAM, SSD de 512 GB y pantalla de 23.8\"."),
    p(VD, "Computadoras de escritorio", "Intel", "PC Core i7 8700 16GB RAM 512GB SSD + Monitor 24\"", "1699.90",
      stock=0, alerta="agotado", descripcion="Computadora armada con Intel Core i7 8700, 16 GB de RAM, SSD de 512 GB y monitor Full HD de 24\"."),
    p(VD, "Accesorios", "Logitech", "Combo Teclado y Mouse Logitech MK270 Inalámbrico", "129", stock=3,
      alerta="bajo", descripcion="Teclado y mouse inalámbricos con receptor USB.",
      enlace=falabella("product/117794405/Combo-Teclado-Mouse-Logitech-MK270-Inalambrico-Multimedia-Negro/117794406")),
    p(VD, "Accesorios", "Redragon", "Teclado Mecánico Redragon Kumara K552 Rainbow Español", "175", stock=6,
      alerta="sin_costo", descripcion="Teclado mecánico TKL con retroiluminación rainbow, distribución en español.",
      enlace=falabella("product/114059349/Teclado-mecanico-redragon-kumara-k552-rainbow-espanol-negro/114059350")),
    p(VD, "Tablets", "Apple", "iPad 11 Chip A16 Wi-Fi 128GB", "1899", stock=4,
      descripcion="iPad de 11 pulgadas con chip A16, Wi-Fi y 128 GB."),
    p(VD, "Tablets", "Lenovo", "Tablet Lenovo Idea Tab 11\" 2.5K 8GB 128GB", "949", stock=5,
      descripcion="MediaTek Dimensity 6300, pantalla 2.5K de 90 Hz, 8 GB de RAM y 128 GB."),

    # --- Kantu Tech: impresoras, seguridad, repuestos y redes ---------------------------------
    p(KT, "Impresoras y suministros", "Epson", "Impresora Multifuncional Epson EcoTank L3350 Wi-Fi", "789", stock=6,
      destacado=True, descripcion="Imprime, copia y escanea con tanques de tinta recargables y Wi-Fi."),
    p(KT, "Impresoras y suministros", "HP", "Impresora Multifuncional HP Smart Tank 580 Wi-Fi", "499", stock=5,
      descripcion="Sistema continuo de tinta, Wi-Fi e impresión desde el celular con la app HP."),
    p(KT, "Impresoras y suministros", "Canon", "Impresora Multifuncional Canon Pixma G4170", "1149", oferta="869",
      stock=4, descripcion="Multifuncional de tinta continua con Wi-Fi y fax."),
    p(KT, "Impresoras y suministros", "Brother", "Impresora Multifuncional Brother DCP-T530DW Wi-Fi Dúplex", "659",
      stock=4, alerta="sin_costo", descripcion="Tanque de tinta InkBenefit, Wi-Fi e impresión a doble cara automática."),
    p(KT, "Impresoras y suministros", "Canon", "Tinta Canon GI-190 Kit x4 Colores", "115", stock=3, alerta="bajo",
      descripcion="Kit de 4 botellas de tinta (negro, cian, magenta y amarillo) para impresoras Canon Pixma G."),
    p(KT, "Seguridad y videovigilancia", "TP-Link", "Cámara de Seguridad TP-Link Tapo C200 Wi-Fi 360° 1080p", "119",
      oferta="89.90", stock=10, descripcion="Cámara para interiores con giro 360°, visión nocturna y audio bidireccional.",
      enlace=falabella("product/115495048/Camara-de-seguridad-para-interiores-Tapo-C200-Tp-Link/115495049")),
    p(KT, "Seguridad y videovigilancia", "Ezviz", "Cámara de Seguridad Ezviz C6N G1 3K Wi-Fi 6 360°", "129", stock=8,
      destacado=True, descripcion="Cámara para interiores de 5 MP (3K) con giro 360°, Wi-Fi 6 y detección con IA."),
    p(KT, "Seguridad y videovigilancia", "Tenda", "Cámara de Seguridad Exterior Tenda CH7 2.5K Wi-Fi 360°", "109.90",
      stock=7, descripcion="Cámara para exteriores con doble antena, giro panorámico y visión nocturna a color."),
    p(KT, "Seguridad y videovigilancia", "Hikvision", "Kit 4 Cámaras Hikvision Full HD 1080p + Disco Seagate", "763",
      stock=2, alerta="bajo", descripcion="Kit de videovigilancia con 4 cámaras Full HD y disco duro para grabación."),
    p(KT, "Seguridad y videovigilancia", "Dahua", "Kit 6 Cámaras Dahua 1080p Varifocal + Disco 2TB", "1689", stock=0,
      alerta="agotado", descripcion="Kit de 6 cámaras 1080p de mayor alcance (varifocales) con disco de 2 TB."),
    p(KT, "Repuestos", "Kingston", "Memoria RAM Kingston Fury Beast 16GB DDR4 3200MHz", "699", stock=6,
      descripcion="Módulo de 16 GB DDR4 a 3200 MHz para PC de escritorio."),
    p(KT, "Repuestos", "Kingston", "Disco SSD Kingston NV3 1TB M.2 NVMe PCIe 4.0", "740", stock=5, destacado=True,
      descripcion="Unidad SSD M.2 2280 de 1 TB, NVMe PCIe 4.0 (SNV3S/1000G).",
      enlace=falabella("product/135574822/Disco-Solido-SSD-Kingston-NV3-1TB-M2-2280-NMVe-PCIe-4.0-SNV3S-1000G/135574823")),
    p(KT, "Repuestos", "Western Digital", "Disco SSD WD Green SN3000 1TB M.2 NVMe", "725", stock=4,
      alerta="sin_costo", descripcion="Unidad SSD M.2 2280 de 1 TB, NVMe PCIe 4.0."),
    p(KT, "Repuestos", "AMD", "Procesador AMD Ryzen 5 5600G 3.9GHz AM4", "759", stock=4,
      descripcion="6 núcleos, hasta 4.4 GHz, con gráficos Radeon integrados. Socket AM4.",
      enlace=falabella("product/128131390/PROCESADOR-AMD-RYZEN-5-5600G-3.9GHZ-4.4GHZ-16MB-P-N:-100-100000252BOX/128131391")),
    p(KT, "Repuestos", "Corsair", "Fuente de Poder Corsair CX650 650W 80 Plus Bronze", "459", oferta="269", stock=5,
      descripcion="Fuente ATX de 650 W con certificación 80 Plus Bronze."),
    p(KT, "Otros", "TP-Link", "Router TP-Link Archer AX12 Wi-Fi 6 AX1500", "149", stock=6, alerta="sin_costo",
      descripcion="Router Wi-Fi 6 de doble banda, hasta 1500 Mbps."),
    p(KT, "Otros", "Forza", "UPS Forza NT-1012U 1000VA 500W", "279", stock=2, alerta="bajo",
      descripcion="UPS de 1000 VA / 500 W con 6 salidas, para proteger PC y equipos de la tienda."),
]


# ---------------------------------------------------------------------------
# Cálculos
# ---------------------------------------------------------------------------

def costo_demo(precio_final, posicion):
    """Costo estimado entre el 70 % y el 80 % del precio que paga el cliente (redondeado a soles)."""
    porcentaje = PORCENTAJES_COSTO[posicion % len(PORCENTAJES_COSTO)]
    return (precio_final * porcentaje).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def stock_minimo_de(dato):
    """Los productos con stock bajo o agotados tienen stock mínimo 3; los demás, 2."""
    return STOCK_MINIMO if dato["alerta"] in ("bajo", "agotado") else 2


def _obtener(modelo, nombre):
    """Busca la categoría o marca sin importar mayúsculas; si no existe, la crea."""
    return modelo.objects.filter(nombre__iexact=nombre).first() or modelo.objects.create(nombre=nombre)


# ---------------------------------------------------------------------------
# Cargar
# ---------------------------------------------------------------------------

def _crear_tienda(datos, grupo_tienda):
    """Crea la tienda (activa y verificada) con su cuenta y horario. Devuelve (tienda, aviso)."""
    tienda = Tienda.objects.filter(nombre__iexact=datos["nombre"]).first()
    if tienda is not None:
        return tienda, None
    if User.objects.filter(username__iexact=datos["usuario"]).exists():
        return None, f"El usuario '{datos['usuario']}' ya existe y no tiene la tienda {datos['nombre']}: se omitió."
    otra = Tienda.objects.filter(whatsapp=datos["whatsapp"]).first()
    if otra is not None:
        return None, f"El WhatsApp {datos['whatsapp']} ya lo usa la tienda {otra.nombre}: se omitió {datos['nombre']}."
    usuario = User.objects.create_user(
        datos["usuario"], correo_demo(datos["usuario"]), CLAVE_DEMO,
        first_name=datos["nombres"], last_name=datos["apellidos"],
    )
    usuario.groups.add(grupo_tienda)
    tienda = Tienda.objects.create(
        usuario=usuario, nombre=datos["nombre"], direccion=datos["direccion"], whatsapp=datos["whatsapp"],
        descripcion=datos["descripcion"], estado=Tienda.Estado.ACTIVA, verificada_en=timezone.now(),
    )
    for dia, tramo in enumerate(datos["horario"]):
        abre, cierra, descanso_inicio, descanso_fin = tramo or (None, None, None, None)
        HorarioDia.objects.create(
            tienda=tienda, dia=dia, abre=abre, cierra=cierra,
            descanso_inicio=descanso_inicio, descanso_fin=descanso_fin,
        )
    return tienda, "creada"


def _crear_producto(tienda, dato, posicion):
    producto = Producto(
        tienda=tienda, categoria=_obtener(Categoria, dato["categoria"]), marca=_obtener(Marca, dato["marca"]),
        nombre=dato["nombre"], descripcion=dato["descripcion"], precio=dato["precio"],
        precio_oferta=dato["oferta"], oferta_hasta=dato["hasta"], stock=dato["stock"],
        destacado=dato["destacado"],
    )
    producto._usuario_cambio = tienda.usuario  # el kardex anota quién registró el inventario inicial
    producto.save()
    FichaInventario.objects.create(
        producto=producto,
        costo=None if dato["alerta"] == "sin_costo" else costo_demo(producto.precio_final, posicion),
        stock_minimo=stock_minimo_de(dato),
        codigo=f"{''.join(palabra[0] for palabra in tienda.nombre.split()).upper()}-{posicion + 1:03d}",
    )
    return producto


def mover_monitor_acer():
    """Corrección: el monitor Acer KA242Y estaba en Accesorios; va en Pantallas."""
    pantallas = _obtener(Categoria, "Pantallas")
    movidos = 0
    for producto in Producto.objects.filter(nombre__istartswith="Monitor Acer KA242Y").exclude(categoria=pantallas):
        producto.categoria = pantallas
        producto.save()  # guardado completo: también actualiza el texto de búsqueda
        movidos += 1
    return movidos


def cargar():
    """Crea las tiendas y productos que falten. Devuelve un resumen."""
    resumen = {"tiendas": [], "productos": 0, "existentes": 0, "avisos": [], "monitor_movido": 0}
    grupo_tienda, _ = Group.objects.get_or_create(name="Tienda")
    tiendas = {}
    with transaction.atomic():
        for datos in TIENDAS:
            tienda, aviso = _crear_tienda(datos, grupo_tienda)
            if tienda is not None:
                tiendas[datos["nombre"]] = tienda
            if aviso == "creada":
                resumen["tiendas"].append(tienda.nombre)
            elif aviso:
                resumen["avisos"].append(aviso)

        posiciones = {}
        for dato in PRODUCTOS:
            tienda = tiendas.get(dato["tienda"])
            posicion = posiciones.get(dato["tienda"], 0)
            posiciones[dato["tienda"]] = posicion + 1
            if tienda is None:
                continue
            if Producto.objects.filter(tienda=tienda, nombre__iexact=dato["nombre"]).exists():
                resumen["existentes"] += 1
                continue
            _crear_producto(tienda, dato, posicion)
            resumen["productos"] += 1

        resumen["monitor_movido"] = mover_monitor_acer()
    return resumen


def enlaces_markdown():
    """Lista de enlaces para buscar la foto de cada producto (se guarda en Claude outputs)."""
    lineas = [
        "# Fotos de los productos de presentación",
        "",
        f"Precios tomados de {FUENTE}. Abre el enlace, guarda la foto del producto y súbela en "
        "**Mis productos → Editar → Foto principal** de la tienda que corresponde.",
        "",
    ]
    for tienda in TIENDAS:
        lineas += [f"## {tienda['nombre']} (usuario `{tienda['usuario']}`)", "",
                   "| # | Producto | Categoría | Dónde ver la foto |", "|---|---|---|---|"]
        numero = 0
        for dato in PRODUCTOS:
            if dato["tienda"] != tienda["nombre"]:
                continue
            numero += 1
            nombre = dato["nombre"].replace("|", "/")
            lineas.append(f"| {numero} | {nombre} | {dato['categoria']} | [Abrir]({dato['enlace']}) |")
        lineas.append("")
    return "\n".join(lineas)
