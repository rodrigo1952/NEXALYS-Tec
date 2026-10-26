# NEXALYS Tec

Plataforma web donde las tiendas tecnológicas publican sus productos y los clientes los encuentran, comparan y contactan a la tienda por WhatsApp.

Proyecto del IV ciclo de Arquitectura de Plataformas y Servicios de TI — IESPP Urusayhua.

## Tecnologías

- Python 3.12 o superior
- Django 6.1
- SQLite (base de datos de desarrollo)
- Bootstrap 5 (interfaz)
- Pillow (imágenes de productos)

## Instalación

```powershell
git clone https://github.com/rodrigo1952/NEXALYS-Tec.git nexalys
cd nexalys
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\activate
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
| Administrador | `createsuperuser` | Panel propio en `/panel/admin/`: resumen, tiendas (suspender con motivo / reactivar), productos (ocultar con motivo), pedidos (consulta), usuarios (desactivar, reactivar, eliminar), categorías y marcas |
| Tienda | Registro en "Registrar mi tienda" + verificación del correo | Gestionar sus productos (con ofertas, destacados y varias fotos), sus pedidos, sus datos, su logo y su horario |
| Cliente | Registro en "Registrarse" | Guardar favoritos, editar sus datos, cambiar o recuperar su contraseña y eliminar su cuenta (el catálogo es público) |

## Módulos CRUD

| Módulo | Rol | Caso de uso | Ruta |
|---|---|---|---|
| Productos | Tienda | CU-03 | `/catalogo/mis-productos/` |
| Categorías y marcas | Administrador | CU-07 | `/catalogo/gestion/categorias/` y `/catalogo/gestion/marcas/` |
| Pedidos | Tienda | CU-08 | `/pedidos/` |

Los tres están integrados: un producto pertenece a una categoría y una marca, y cada pedido descuenta el stock del producto.

### Validaciones

- Campos obligatorios en todos los formularios.
- Precio mínimo S/ 0.10, stock y cantidad no negativos (cantidad mínima 1).
- Imagen JPG/PNG/WEBP de máximo 2 MB.
- Celulares peruanos de 9 dígitos que empiezan con 9.
- Nombres únicos sin importar mayúsculas: tiendas, categorías, marcas y productos de una misma tienda.

### Reglas de negocio

1. La tienda queda **pendiente** al registrarse y se **activa sola** al verificar su correo.
2. Solo las tiendas **activas** gestionan productos y pedidos.
3. Una tienda **no puede ver ni modificar** productos ni pedidos de otra (responde 404).
4. El catálogo público solo muestra productos **publicados** de tiendas **activas**.
5. El administrador puede **suspender** una tienda; sus productos se ocultan.
6. Una categoría o marca **con productos no se elimina**, se desactiva; las inactivas no se ofrecen en productos nuevos.
7. Registrar un pedido **descuenta el stock**; no se registra si no hay stock suficiente.
8. El pedido sigue el flujo **pendiente → confirmado → entregado**, y puede **cancelarse** antes de entregarse; cancelar **restituye el stock**.
9. Solo se **editan** pedidos pendientes; los confirmados o entregados **no se eliminan** (historial de ventas).
10. Un producto **con pedidos no se elimina**; se puede ocultar.
11. Solo los **clientes** tienen favoritos; un producto aparece **una sola vez** en la lista de cada cliente.
12. Si un visitante toca el corazón, va a iniciar sesión y el producto **se guarda solo** al entrar.
13. "Bajó de precio" compara con el **precio que tenía al guardarlo**; el contador del menú muestra las novedades desde la última vez que el cliente abrió "Mis favoritos".
14. Si la tienda elimina el producto, el favorito **se borra**; si lo oculta, se agota o la tienda es suspendida, se muestra **"No disponible"** sin borrarlo.
15. La tienda ve **cuántos** clientes guardaron cada producto, **nunca quiénes**.
16. Para **cambiar el correo** se pide la contraseña actual; solo los clientes pueden **eliminar su cuenta** (se borran también sus favoritos).
17. Una **oferta** vale si su precio es menor que el normal; si tiene fecha de fin, ese día es el último y luego vuelve sola al precio normal. Pedidos, WhatsApp, filtros y orden usan el precio con oferta.
18. Cada tienda puede marcar hasta **3 productos destacados**, que aparecen en el inicio.
19. Cada producto tiene una foto principal y hasta **5 fotos adicionales**.
20. Las imágenes se **optimizan** al subirlas: se giran según la cámara, se reducen (máx. 1200 px; logos 400 px) y se guardan en WEBP.
21. La **búsqueda** no distingue tildes ni mayúsculas, y con varias palabras deben estar todas.
22. La tienda **edita sus datos**, su logo y su **horario** (con **refrigerio** opcional al mediodía); el perfil público muestra si está **abierta ahora**, en refrigerio o cerrada, con horas en formato de 12 horas (a. m. / p. m., hora de Perú).
23. El administrador puede **suspender una tienda** u **ocultar un producto** escribiendo un **motivo** que la tienda ve en su panel; un producto oculto por el administrador no se puede volver a publicar hasta que él lo muestre.
24. El administrador puede **desactivar, reactivar o eliminar** cuentas; no puede modificar su propia cuenta ni la de otros administradores, y una **tienda con pedidos no se elimina** (historial de ventas).
25. **Desactivar la cuenta de una tienda también suspende su tienda** (con el mismo motivo) y oculta sus productos; reactivar la cuenta reactiva la tienda, y reactivar la tienda reactiva la cuenta.
26. Suspender, reactivar, desactivar y eliminar se hacen en **2 pasos**: el botón lleva a una página de confirmación que resume lo que pasará y pide el **motivo** (opcional solo al reactivar). Todo queda en el **Historial** del administrador; una cuenta desactivada ve el motivo al intentar iniciar sesión.
27. **Destacados en Inicio**: primero los más populares de los últimos 30 días (puntaje = vistas + favoritos × 5; 1 vista por visitante al día, sin contar a la propia tienda ni al administrador). Si empatan, primero el que se destacó antes. **Ofertas**: primero el mayor descuento.
28. Las imágenes se guardan en **una carpeta por tienda** (`media/tiendas/<número>-<nombre>/`) con el nombre del producto. Para ordenar las antiguas: `python manage.py ordenar_imagenes`.
29. Una **tienda suspendida que no se reactiva en 90 días se elimina automáticamente** (cuenta, productos e imágenes). La tienda ve la fecha límite en su panel desde el primer día; el administrador ve la lista en el Resumen. Sus ventas se conservan **anónimas** ("Tienda eliminada", sin datos del cliente) y queda registrado en el Historial. La limpieza se ejecuta al entrar al panel del administrador o con `python manage.py limpiar_cuentas`.
30. Los **clientes confirman su correo** antes de poder iniciar sesión (igual que las tiendas). Pueden pedir un enlace nuevo; si no confirman en 7 días, la cuenta se elimina sola. Los clientes registrados antes de esta regla ya cuentan como confirmados.
31. **Mis productos = catálogo + inventario** en una sola sección (reemplazará a Pedidos): la lista muestra precio, publicación, stock y alertas de stock bajo; cada producto tiene una **ficha** privada (costo, stock mínimo, código) y un **kardex** con toda la historia de su stock. El formulario de productos no cambia: si la tienda cambia el stock al editar, queda anotado en el kardex. La tienda guarda su lista de **proveedores**. Costos y proveedores solo los ve la tienda.
32. **Ventas** (pestaña de Mis productos): una venta puede tener varios productos; el precio se sugiere y se puede cambiar (descuentos); se elige el método de pago y, si se quiere, el cliente. El stock se descuenta y queda en el kardex. Cada venta tiene un número correlativo por tienda y una **nota de venta** imprimible (documento interno, no es boleta ni factura). Una venta registrada por error se **anula** con un motivo: no se borra y el stock vuelve. Las anuladas no suman en los totales.

## Control de concurrencia

Situaciones en las que dos personas (o dos pestañas) actúan sobre el mismo dato a la vez, y cómo se controlan:

| Escenario | Control |
|---|---|
| Dos pedidos a la vez por las últimas unidades | Transacción atómica + bloqueo de fila; SQLite con `transaction_mode = IMMEDIATE` |
| Cancelar, confirmar, editar o eliminar el mismo pedido a la vez | El pedido se vuelve a leer y se bloquea dentro de la transacción |
| Editar un producto que otra pestaña o un pedido acaba de cambiar | Bloqueo optimista con la versión del producto (campo oculto `version`) |
| Registro simultáneo con el mismo usuario, correo, tienda o WhatsApp | Validar y guardar en una transacción; el duplicado se muestra como error del formulario |
| Eliminar un producto justo cuando se le registra un pedido | Eliminación en transacción; se avisa en vez de mostrar error 500 |
| Dos ventas a la vez por las últimas unidades, o el mismo producto en dos líneas | Productos bloqueados en orden por id y stock releído en la transacción; las cantidades del mismo producto se suman |
| Dos ventas a la vez en la misma tienda (número de venta) | La tienda se bloquea al numerar: el número no se repite |
| Anular la misma venta dos veces | La venta se relee bloqueada; la segunda anulación se rechaza |
| Doble clic en un botón de enviar | Los botones se desactivan al enviar ("Procesando…") |

Las pruebas están en `pedidos/test_concurrencia.py`, `catalogo/test_concurrencia.py`, `cuentas/test_concurrencia.py` e `inventario/test_ventas.py`.

## Permisos por rol

| Acción | Visitante | Cliente | Tienda | Administrador |
|---|:-:|:-:|:-:|:-:|
| Ver catálogo | ✅ | ✅ | ✅ | ✅ |
| Guardar favoritos | | ✅ | | |
| Editar datos y cambiar contraseña | | ✅ | ✅ | ✅ |
| Eliminar su cuenta | | ✅ | | |
| Gestionar sus productos y pedidos | | | ✅ | |
| Gestionar categorías y marcas | | | | ✅ |
| Suspender tiendas / Django Admin | | | | ✅ |

## Datos de demostración

GitHub guarda el código, pero no la base de datos (`db.sqlite3`) ni las imágenes (`media/`). Para tener las mismas tiendas y productos en otra PC:

```
python manage.py exportar_demo    # en la PC que tiene los datos; luego git add demo, commit y push
python manage.py cargar_demo      # en la otra PC, después de git pull y migrate
```

No se exportan clientes, pedidos, favoritos ni contraseñas. Las cuentas de tienda cargadas usan la contraseña `Demo#2026`.

## Administración de la base de datos

- **Panel de administración** (`/panel/admin/`): pantallas con el diseño de NEXALYS para el trabajo diario del Administrador.
- **Django Admin** (`/admin/`): herramienta avanzada con todas las tablas, como respaldo.
- **DB Browser for SQLite** (https://sqlitebrowser.org): abrir el archivo `db.sqlite3` para ver la estructura de las tablas y sus registros.

En desarrollo, los correos se muestran en la consola donde corre `runserver`.
Los enlaces de verificación de tienda y de recuperación de contraseña también se imprimen completos con el prefijo `[NEXALYS]`.
