# NEXALYS Tec

Plataforma web donde las tiendas tecnológicas publican sus productos y los clientes los encuentran, comparan y contactan a la tienda por WhatsApp.

Proyecto del IV ciclo de Arquitectura de Plataformas y Servicios de TI — IESPP Urusayhua.

## Tecnologías

- Python 3.14
- Django 6.1.1
- SQLite (base de datos de desarrollo)
- Bootstrap 5.3.3 (interfaz)
- Chart.js (gráficos del Resumen)
- Pillow (imágenes de productos)
- openpyxl (descarga en Excel)

## Instalación

Se usa `py -3.14` para crear el entorno virtual porque en algunas PC el comando `python` abre otra versión de Python.

```powershell
git clone https://github.com/rodrigo1952/NEXALYS-Tec.git nexalys
cd nexalys
py -3.14 -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\activate
python --version    # debe decir Python 3.14.x
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abrir `http://127.0.0.1:8000`.

## Pruebas automáticas

```powershell
python manage.py test -v 2
```

## Roles

| Rol | Cómo se obtiene | Qué puede hacer |
|---|---|---|
| Administrador | `createsuperuser` | Panel propio en `/panel/admin/`: resumen, tiendas (suspender con motivo / reactivar), productos (ocultar con motivo), ventas (totales por tienda y mes), usuarios (desactivar, reactivar, eliminar), categorías y marcas |
| Tienda | Registro en "Registrar mi tienda" + verificación del correo | Gestionar sus productos (con ofertas, destacados y varias fotos), su inventario y sus ventas, sus datos, su logo y su horario |
| Cliente | Registro en "Registrarse" | Guardar favoritos, editar sus datos, cambiar o recuperar su contraseña y eliminar su cuenta (el catálogo es público) |

## Módulos CRUD

| Módulo | Rol | Caso de uso | Ruta |
|---|---|---|---|
| Productos | Tienda | CU-03 | `/catalogo/mis-productos/` |
| Categorías y marcas | Administrador | CU-07 | `/catalogo/gestion/categorias/` y `/catalogo/gestion/marcas/` |
| Ventas (inventario) | Tienda | CU-08 | `/inventario/ventas/` |

Los tres están integrados: un producto pertenece a una categoría y una marca, y cada venta descuenta el stock del producto.

### Validaciones

- Campos obligatorios en todos los formularios.
- Precio mínimo S/ 0.10, stock y cantidad no negativos (cantidad mínima 1).
- Imagen JPG/PNG/WEBP de máximo 2 MB.
- Celulares peruanos de 9 dígitos que empiezan con 9.
- Nombres únicos sin importar mayúsculas: tiendas, categorías, marcas y productos de una misma tienda.

### Reglas de negocio

1. La tienda queda **pendiente** al registrarse y se **activa sola** al verificar su correo.
2. Solo las tiendas **activas** gestionan productos, inventario y ventas.
3. Una tienda **no puede ver ni modificar** productos, ventas ni inventario de otra (responde 404).
4. El catálogo público solo muestra productos **publicados** de tiendas **activas**.
5. El administrador puede **suspender** una tienda; sus productos se ocultan.
6. Una categoría o marca **con productos no se elimina**, se desactiva; las inactivas no se ofrecen en productos nuevos.
7. Registrar una **venta descuenta el stock**; no se registra si no hay stock suficiente (de ningún producto de la venta).
8. Una venta registrada por error se **anula con un motivo**: no se borra y **el stock vuelve**.
9. Las ventas **no se editan ni se eliminan** (historial); se anulan.
10. Un producto **se puede eliminar aunque tenga ventas**: sus ventas, ingresos y kardex conservan el nombre del producto.
11. Solo los **clientes** tienen favoritos; un producto aparece **una sola vez** en la lista de cada cliente.
12. Si un visitante toca el corazón, va a iniciar sesión y el producto **se guarda solo** al entrar.
13. "Bajó de precio" compara con el **precio que tenía al guardarlo**; el contador del menú muestra las novedades desde la última vez que el cliente abrió "Mis favoritos".
14. Si la tienda elimina el producto, el favorito **se borra**; si lo oculta, se agota o la tienda es suspendida, se muestra **"No disponible"** sin borrarlo.
15. La tienda ve **cuántos** clientes guardaron cada producto, **nunca quiénes**.
16. Para **cambiar el correo** se pide la contraseña actual; solo los clientes pueden **eliminar su cuenta** (se borran también sus favoritos).
17. Una **oferta** vale si su precio es menor que el normal; si tiene fecha de fin, ese día es el último y luego vuelve sola al precio normal. Ventas, WhatsApp, filtros y orden usan el precio con oferta.
18. Cada tienda puede marcar hasta **3 productos destacados**, que aparecen en el inicio.
19. Cada producto tiene una foto principal y hasta **5 fotos adicionales**.
20. Las imágenes se **optimizan** al subirlas: se giran según la cámara, se reducen (máx. 1200 px; logos 400 px) y se guardan en WEBP.
21. La **búsqueda** no distingue tildes ni mayúsculas, y con varias palabras deben estar todas.
22. La tienda **edita sus datos**, su logo y su **horario** (con **refrigerio** opcional al mediodía); el perfil público muestra si está **abierta ahora**, en refrigerio o cerrada, con horas en formato de 12 horas (a. m. / p. m., hora de Perú).
23. El administrador puede **suspender una tienda** u **ocultar un producto** escribiendo un **motivo** que la tienda ve en su panel; un producto oculto por el administrador no se puede volver a publicar hasta que él lo muestre.
24. El administrador puede **desactivar, reactivar o eliminar** cuentas; no puede modificar su propia cuenta ni la de otros administradores, y una **tienda con ventas no se elimina** (historial de ventas).
25. **Desactivar la cuenta de una tienda también suspende su tienda** (con el mismo motivo) y oculta sus productos; reactivar la cuenta reactiva la tienda, y reactivar la tienda reactiva la cuenta.
26. Suspender, reactivar, desactivar y eliminar se hacen en **2 pasos**: el botón lleva a una página de confirmación que resume lo que pasará y pide el **motivo** (opcional solo al reactivar). Todo queda en el **Historial** del administrador; una cuenta desactivada ve el motivo al intentar iniciar sesión.
27. **Destacados en Inicio**: primero los más populares de los últimos 30 días (puntaje = vistas + favoritos × 5; 1 vista por visitante al día, sin contar a la propia tienda ni al administrador). Si empatan, primero el que se destacó antes. **Ofertas**: primero el mayor descuento.
28. Las imágenes se guardan en **una carpeta por tienda** (`media/tiendas/<número>-<nombre>/`) con el nombre del producto. Para ordenar las antiguas: `python manage.py ordenar_imagenes`.
29. Una **tienda suspendida que no se reactiva en 90 días se elimina automáticamente** (cuenta, productos e imágenes). La tienda ve la fecha límite en su panel desde el primer día; el administrador ve la lista en el Resumen. Sus ventas se conservan **anónimas** ("Tienda eliminada", sin datos del cliente) y queda registrado en el Historial. La limpieza se ejecuta al entrar al panel del administrador o con `python manage.py limpiar_cuentas`.
30. Los **clientes confirman su correo** antes de poder iniciar sesión (igual que las tiendas). Pueden pedir un enlace nuevo; si no confirman en 7 días, la cuenta se elimina sola. Los clientes registrados antes de esta regla ya cuentan como confirmados.
31. **Mis productos = catálogo + inventario** en una sola sección (reemplazó a Pedidos): la lista muestra precio, publicación, stock y alertas de stock bajo; cada producto tiene datos privados (precio de compra, stock mínimo, código) y un **kardex** con toda la historia de su stock. Si la tienda cambia el stock al editar un producto, queda anotado en el kardex. La tienda guarda su lista de **proveedores**. Costos y proveedores solo los ve la tienda.
32. **Ventas** (pestaña de Mis productos): una venta puede tener varios productos; el precio se sugiere y se puede cambiar (descuentos); se elige el método de pago y, si se quiere, el cliente. El stock se descuenta y queda en el kardex. Cada venta tiene un número correlativo por tienda y una **nota de venta** imprimible (documento interno, no es boleta ni factura). Una venta registrada por error se **anula** con un motivo: no se borra y el stock vuelve. Las anuladas no suman en los totales.
33. **Ingresos, ajustes y conteo físico** (pestañas de Mis productos). Un **ingreso** registra la mercadería recibida (varios productos, proveedor y factura o guía opcionales): suma stock y actualiza el **costo promedio** de la ficha. Un ingreso equivocado se anula con motivo, salvo que ya se haya vendido parte de esas unidades. Los **ajustes** corrigen daños, pérdidas y devoluciones (de un cliente suma; al proveedor resta). El **conteo físico** permite escribir lo contado en el local para varios productos a la vez: solo se corrigen los que tienen diferencia, y si el stock cambió mientras se contaba (por una venta), ese producto no se toca y se pide volver a contarlo. Todo queda en el kardex.
34. **Precio de compra**: el formulario de producto tiene «Precio de compra» y «Precio de venta» en la misma fila. El precio de compra es opcional y privado; es el mismo dato que el costo de la ficha (se puede editar en los dos lados) y al editar muestra el costo promedio actual. En Mis productos se marcan los productos a los que les falta, y se pueden filtrar. Desde «Nuevo ingreso» y «Nueva venta» se puede crear un producto que aún no existe y volver con él ya elegido.
35. **Buscador de productos** en Nuevo ingreso, Nueva venta y Nuevo ajuste: se escribe parte del nombre, el código, la marca o la categoría (en cualquier orden, sin importar mayúsculas ni tildes) y la lista se reduce al instante. Cada resultado muestra código y stock (en ventas, también el precio). Funciona con lector de código de barras: si lo escaneado coincide con un código, el producto se elige solo. Si el JavaScript no carga, se ve la lista normal.
36. **Resumen** (primera pestaña de Mis productos): total vendido, ganancia y margen, ticket promedio y valor del inventario del periodo elegido (hoy, 7 días, este mes, mes anterior, este año o un rango de fechas); gráfico de ventas y ganancia por día (o por mes en rangos largos) y de métodos de pago; más vendidos; productos **sin movimiento** (más de 60 días sin venderse) y **alertas** de stock bajo o agotado, que también se ven como un número junto a «Mis productos» en el menú. La ganancia usa el costo del momento de cada venta; lo vendido sin precio de compra no cuenta y se avisa. Se puede **imprimir** o **descargar en Excel** (un archivo con hojas: Resumen, Ventas, Productos vendidos, Inventario valorizado y Sin movimiento). Las ventas anuladas no cuentan. Todo es privado de cada tienda.
37. **Se retiró la sección Pedidos** (Etapa 5): los pedidos pendientes, confirmados y entregados se convirtieron en ventas (con origen «Pedido #N», el celular del cliente en la nota y método de pago «Otro»); los cancelados no. El panel de la tienda tiene «+ Nueva venta» y «+ Nuevo ingreso». El administrador ve en **Ventas** una tabla con el total vendido por cada tienda en los últimos 6 meses (sin anuladas); nunca ve costos, ganancias, proveedores ni clientes. Cuando una tienda suspendida se elimina sola, sus ventas quedan anónimas como «Tienda eliminada» y su kardex, ingresos y proveedores se borran.
38. **Formulario de producto en filas de dos**: precio de compra | precio de venta, precio de oferta | válida hasta, y stock actual | stock mínimo (el stock mínimo es el mismo dato de la ficha de inventario y sirve para las alertas). **Panel de la tienda**: se abre tocando el nombre de la tienda junto a «Cerrar sesión» (ya no hay «Mi tienda» en el menú); reúne los datos de la tienda y de la cuenta, con el logo grande (o la inicial) junto al nombre y los botones «Ver mi tienda pública», «Editar datos de mi cuenta» y «Cambiar contraseña». La página «Mi cuenta» queda para clientes y administradores.
39. **Menú de la cuenta**: el nombre del usuario (junto al buscador) abre un desplegable con su nombre, rol, correo parcialmente oculto y, en las tiendas, su estado; y las opciones Mi tienda (solo tiendas), Mi cuenta (para todos los roles: datos, editar y cambiar contraseña), Ayuda y soporte (preguntas frecuentes por rol y correo de soporte), Privacidad y términos (Ley 29733) y Cerrar sesión, que pide confirmación (Sí / No). El panel de la tienda muestra «Ver mi tienda pública» junto al nombre. **Contraseña para datos sensibles**: cambiar el nombre o el correo de la cuenta, o el nombre, la dirección o el WhatsApp de la tienda, pide la contraseña actual; luego no se vuelve a pedir durante 10 minutos. No se pide para la descripción, el logo, el horario ni los productos. **Sin repeticiones**: la Ficha de inventario se retiró (el código interno, el precio de compra y el stock mínimo se editan en el formulario del producto) y Mis productos usa filtros rápidos (Stock bajo, Agotados, Sin precio de compra) en vez de tarjetas; los números completos están en Resumen.
40. **Fotos al editar un producto**: una galería con todas las fotos (la principal marcada) y un botón para cada cambio: cambiar o quitar la principal, hacer principal una adicional, reemplazar o quitar una adicional y «+ Agregar fotos» (indica cuántas quedan). Los botones muestran qué pasará y todo se aplica al presionar «Guardar»; quitar una foto pide confirmación. Categoría y marca van en la misma fila.

## Control de concurrencia

Situaciones en las que dos personas (o dos pestañas) actúan sobre el mismo dato a la vez, y cómo se controlan:

| Escenario | Control |
|---|---|
| Dos ventas a la vez por las últimas unidades (formulario) | Transacción atómica + bloqueo de fila; SQLite con `transaction_mode = IMMEDIATE` |
| Editar un producto que otra pestaña o una venta acaba de cambiar | Bloqueo optimista con la versión del producto (campo oculto `version`) |
| Registro simultáneo con el mismo usuario, correo, tienda o WhatsApp | Validar y guardar en una transacción; el duplicado se muestra como error del formulario |
| Dos ventas a la vez por las últimas unidades, o el mismo producto en dos líneas | Productos bloqueados en orden por id y stock releído en la transacción; las cantidades del mismo producto se suman |
| Dos ventas a la vez en la misma tienda (número de venta) | La tienda se bloquea al numerar: el número no se repite |
| Anular la misma venta dos veces | La venta se relee bloqueada; la segunda anulación se rechaza |
| Anular un ingreso cuyas unidades ya se vendieron | Se revisa el stock con los productos bloqueados; si no alcanza, no se anula |
| Conteo físico mientras se registra una venta | Se compara el stock que vio la página con el actual; si cambió, ese producto no se corrige |
| Doble clic en un botón de enviar | Los botones se desactivan al enviar ("Procesando…") |

Las pruebas están en `catalogo/test_concurrencia.py`, `cuentas/test_concurrencia.py`, `inventario/test_ventas.py` e `inventario/test_ingresos.py`.

## Permisos por rol

| Acción | Visitante | Cliente | Tienda | Administrador |
|---|:-:|:-:|:-:|:-:|
| Ver catálogo | ✅ | ✅ | ✅ | ✅ |
| Guardar favoritos | | ✅ | | |
| Editar datos y cambiar contraseña | | ✅ | ✅ | ✅ |
| Eliminar su cuenta | | ✅ | | |
| Gestionar sus productos, inventario y ventas | | | ✅ | |
| Gestionar categorías y marcas | | | | ✅ |
| Suspender tiendas / Django Admin | | | | ✅ |

## Datos de demostración

GitHub guarda el código, pero no la base de datos (`db.sqlite3`) ni las imágenes (`media/`). Para tener las mismas tiendas y productos en otra PC:

```
python manage.py exportar_demo    # en la PC que tiene los datos; luego git add demo, commit y push
python manage.py cargar_demo      # en la otra PC, después de git pull y migrate
```

No se exportan clientes, ventas, inventario, favoritos ni contraseñas. Las cuentas de tienda cargadas usan la contraseña `Demo#2026`.

## Administración de la base de datos

- **Panel de administración** (`/panel/admin/`): pantallas con el diseño de NEXALYS para el trabajo diario del Administrador.
- **Django Admin** (`/admin/`): herramienta avanzada con todas las tablas, como respaldo.
- **DB Browser for SQLite** (https://sqlitebrowser.org): abrir el archivo `db.sqlite3` para ver la estructura de las tablas y sus registros.

En desarrollo, los correos se muestran en la consola donde corre `runserver`.
Los enlaces de verificación de tienda y de recuperación de contraseña también se imprimen completos con el prefijo `[NEXALYS]`.
