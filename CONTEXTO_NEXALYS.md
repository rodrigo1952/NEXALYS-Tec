# Contexto de NEXALYS Tec (para continuar en un chat nuevo)

> **Para Claude:** lee este archivo completo antes de empezar. Resume el proyecto, cómo trabajamos
> y lo que está pendiente. El código del repositorio es la fuente de verdad: si algo de aquí no
> coincide con el código, manda el código (y avisa al usuario).

## 1. Qué es el proyecto

- **NEXALYS Tec**: marketplace web donde las tiendas de tecnología de **Quillabamba** publican sus
  productos y los clientes los encuentran y contactan a la tienda por **WhatsApp** (no hay pago en línea).
- Proyecto de curso del IV ciclo (IESTP Urusayhua). Empresa del caso: Logical Center S.R.L.
- Repositorio (público): https://github.com/rodrigo1952/NEXALYS-Tec.git — rama `main`.
- Estado: funciona en local (aún no publicada). Plan: promocionarla de tienda en tienda y luego
  publicarla (hosting para Django + dominio .pe).

## 2. Tecnología

- Python 3.14 (Windows; el venv se crea con `py -3.14 -m venv venv` y VS Code usa ese intérprete), **Django 6.1.1**, SQLite (`transaction_mode` IMMEDIATE), Pillow, openpyxl.
- Bootstrap 5.3.3 y Bootstrap Icons 1.11.3 (jsDelivr), Chart.js 4.4.1 y **Leaflet 1.9.4** (cdnjs) con los mapas de
  **OpenStreetMap** (sin clave ni costo). Letra Space Grotesk (Google Fonts); el logo animado de Inicio usa Lilita One.
- Marca "Circuito": azul marino `#0B1B3A`, cian `#19C3E6`, fondo `#F3F6FA` (variables `--nx-*` en `static/css/marca.css`).
  Si se cambia `marca.css`, subir el número `?v=` en `templates/base.html` (va en **v=31**).
  Lo mismo con los scripts propios: `galeria_producto.js?v=5`, `catalogo.js?v=2`, `mapas.js?v=1`, `horario.js?v=2`, `whatsapp.js?v=2`.
  Tarjetas, campos de formulario y **filas de todas las tablas en blanco** en todo el sitio (el fondo de la página
  sigue gris claro); al enfocar un campo, borde y brillo cian; al pasar el mouse por una fila, celeste muy suave.
- `db.sqlite3`, `media/` y `.vscode/` **no** van a GitHub (`.gitignore`). Para llevar datos de prueba a otra PC:
  `python manage.py exportar_demo` / `python manage.py cargar_demo` (ver README).
- Para la presentación: `python manage.py cargar_productos_presentacion` crea 3 tiendas ficticias
  (Selva Byte, Valle Digital Tech, Kantu Tech; WhatsApp del equipo 930909090, 920909090, 910909090)
  con 47 productos reales (datos en `catalogo/presentacion.py`). Las fotos de esos productos el usuario
  ya las subió a mano en su PC (están en su `media/` y en su `db.sqlite3`, no en GitHub).

## 3. Roles y módulos

- **Visitante**: ve el catálogo sin registrarse y la página **Tiendas cercanas** (mapa + lista por distancia).
- **Cliente**: favoritos con avisos dentro de la página (sin correo). No hay reseñas.
- **Tienda**: se registra como "pendiente" y se activa al confirmar su correo. Gestiona productos
  (varias fotos, ofertas con fecha fin opcional, hasta 3 destacados), perfil con horario por día,
  logo, dirección y **ubicación del local en el mapa** (opcional, con pin). Inventario completo:
  - ventas con nota de venta para imprimir;
  - ingresos de mercadería con costo promedio;
  - ajustes, conteo y kardex;
  - alertas de stock bajo;
  - resumen con gráficos y descarga en Excel.
- **Administrador**: suspende/reactiva tiendas, gestiona categorías y marcas, usuarios, y ve solo el
  **total vendido por tienda y mes**.
- El módulo "Pedidos" se retiró (sus pedidos se convirtieron en ventas). La app `pedidos` queda vacía.

## 4. Reglas que NO se deben romper

- **Privacidad por tienda**: costos, ganancia, proveedores y clientes de cada tienda solo los ve esa
  tienda. El administrador no los ve.
- **Datos sensibles**: cambiar nombre, apellido o correo de la cuenta, y nombre, dirección, WhatsApp o
  **ubicación en el mapa** de la tienda, pide la contraseña otra vez (`cuentas/reautenticacion.py`, válido
  10 minutos). Los productos no la piden.
- **Stock**: solo se escribe al CREAR el producto (inventario inicial). Al editar, el campo «Stock actual» se ve
  bloqueado con enlaces a «Ajustar stock» y «Registrar ingreso»: así todo cambio queda en el kardex con su motivo.
- **Ubicación del cliente**: «Tiendas cercanas» la usa solo en su navegador (distancias); nunca llega al servidor
  ni se guarda (Ley 29733).
- **Login**: el selector "Soy cliente / Soy tienda" se valida. Una tienda debe entrar como tienda y
  un cliente como cliente; el administrador entra con cualquiera. El aviso solo sale si la contraseña
  es correcta. Si eligió mal, la página **marca sola la opción correcta** (brilla con una flechita), deja
  escrito el usuario y pone el cursor en la contraseña. Diseño: tarjeta blanca con dos capas detrás (cian y
  azul marino, clase `pagina-ingreso` en el body), logo N de circuito, selector con íconos y botón «Mostrar» con ojo.
- **Exportación de demo**: nunca exporta contraseñas, clientes, ventas, inventario ni favoritos, y
  reemplaza los correos reales.
- "Otra" (marca) y "Otros" (categoría) van siempre al final de las listas.

## 5. Cómo trabajamos (acuerdos con el usuario)

- Responder en **español**, paso a paso, con palabras simples (el usuario está aprendiendo).
- **Antes de implementar cualquier cosa, hacer una encuesta** (AskUserQuestion) para definir cada
  detalle. Si algo no queda claro, preguntarlo con otra encuesta.
- Si el usuario pide ver un diseño primero, mostrar una vista previa antes de tocar el código.
- No darle la razón por darla: corregirlo cuando se equivoque. Si no se sabe algo, investigar en internet.
- **Nunca hacer commit ni push por él**: él hace commit y push con su nombre. Al final de cada tarea,
  darle los comandos de `git`.
- En la PC del laboratorio, al terminar borra su identidad de git y la credencial de GitHub.
- Respuestas breves cuando él lo pida.

### Forma de editar archivos (Claude en Cowork)

- La carpeta del proyecto está en su PC: `C:\Users\usuario\Documents\nexalys`.
- Antes de editar, **leer (stage) la versión actual de cada archivo** desde su PC; nunca reutilizar
  copias viejas. (Ya pasó una vez que se sobrescribió `_menu_usuario.html` con una copia antigua.)
- Respetar los finales de línea de cada archivo (algunos son CRLF).
- Al escribir de vuelta, usar la fecha de modificación esperada (expectedMtimeMs) para no pisar
  cambios suyos.
- Claude corre las pruebas de Django y revisa las pantallas (Playwright) en su propio entorno antes de
  entregar; aun así, el usuario las vuelve a correr en su PC (`python manage.py test`) y manda capturas.
- Claude no puede borrar archivos en su PC; si algo sobra, le indica cuál borrar.
- El entorno de Claude no llega a los CDN ni a OpenStreetMap: para revisar pantallas con Playwright usa
  simuladores (stub) de Chart.js y de Leaflet; los mapas reales los revisa el usuario en su PC.
- **Ojo con arrastrar fotos**: en Chrome/Brave/Edge, arrastrar una `<img>` de la página también trae la imagen
  como «Files». Para probar un arrastre de verdad hay que simularlo con un `DataTransfer` que incluya un `File`
  (con el arrastre sintético de Playwright el error no aparece).
- Al terminar una tarea: el usuario corre `python manage.py test` (y `migrate` si hay migraciones nuevas),
  prueba en el navegador con **Ctrl + F5** y hace el commit.

## 6. Convenciones del código

- Vistas: `form = Form(request.POST if request.method == "POST" else None)`.
- Operaciones de stock con `select_for_update`, bloqueando productos en orden de id. Kardex en
  `Movimiento` con cantidad con signo.
- Formsets para ventas e ingresos de varias líneas. `{% querystring %}` para filtros y paginación.
- Formularios: el atributo `fila = "inicio"/"fin"` pone dos campos en una misma fila
  (`templates/_campos_formulario.html`); `aparte = True` indica que el campo se dibuja por separado.
- Listas con buscador: un `<select>` con el atributo `data-buscable` usa `static/js/lista_buscable.js`.
- Acciones visibles (no usar enlaces `.small` para acciones): `.btn-volver` (con `<span class="flecha">&larr;</span>`)
  para «Volver a…», `.atajo` + botón para crear lo que falta (p. ej. «+ Crear producto», «+ Nuevo proveedor»)
  y `.enlace-accion` para «Ver más / ver todo» (agrega la flecha →). Están en `marca.css`.
- **Galería de fotos del producto** (al AGREGAR y al EDITAR, arriba de todo el formulario):
  `catalogo/_galeria_edicion.html` + `static/js/galeria_producto.js`. Todas las fotos en una sola lista
  (máximo 6); **la primera es la principal**. **Compacta y SIN botones** (unos 230 px de alto; antes ~780):
  sin fotos, un recuadro bajo («Arrastra tus fotos aquí o elígelas»); con fotos, cuadrícula de 5 columnas con la
  principal 2×2 a la izquierda, las fotos 2-6 a su derecha en dos filas (vacías «+ Foto N») y «Agregar varias»
  (o «Máximo 6 fotos»). En el celular, 3 columnas. Se eligen varias a la vez (en el orden que entrega el
  navegador: Windows NO informa el orden de los clics). **Clic en una foto = reemplazarla**; **arrastrarla sobre
  otra = intercambiarlas** (así se cambia la principal); «✕» al pasar el mouse = quitarla (en el celular se ve
  siempre). Celular: mantener presionada (450 ms) y arrastrar. Teclado: Enter reemplaza, flechas mueven,
  Suprimir quita. Si se quita la principal, sube la siguiente.
  El formulario de producto tiene una **barra fija abajo** («Cancelar» / «Guardar producto»). Al guardar se envía el orden final en el campo
  oculto `galeria_plan` («p» = principal actual, «f12» = foto adicional 12, «n0» = 1.ª foto nueva; «ninguna» = sin
  fotos) y las fotos nuevas en `fotos_nuevas`; el servidor lo aplica en `ProductoForm.aplicar_plan` (las fotos que
  ya existían solo cambian de lugar, sin volver a subirse; luego `reubicar_producto` renombra los archivos).
  Sin `galeria_plan` se usan los campos antiguos (imagen, eliminar_fotos, principal_foto, orden_fotos,
  reemplazar_<id>), que siguen funcionando. Si el formulario tiene errores, el navegador pierde las fotos nuevas
  (la página lo avisa).
- Visor de fotos con flechas, teclado y contador en `static/js/visor.js` (las imágenes con el mismo
  `data-galeria` se recorren juntas).
- Barra de categorías (debajo del menú, en todas las páginas menos el login): las 5 con más movimiento
  (vistas + favoritos × 5 de los últimos 30 días; «Otros» nunca entra) y «☰ Todas las categorías».
  Se calcula en `catalogo/context_processors.py`.
- Tarjeta de producto: toda la tarjeta lleva al detalle (el nombre usa `stretched-link`); ya no hay
  botón «Ver detalle». El corazón y el enlace de la tienda funcionan aparte.
- Catálogo (`catalogo/views.py` + `static/js/catalogo.js`): ruta y título de la categoría, filtros a la
  izquierda (en stock, ofertas, precio con deslizador, varias marcas y tiendas con su cantidad) que se
  aplican al instante en computadora (en el celular, panel «Filtrar» + «Ver resultados»), chips para
  quitar filtros, orden y vista 4/3/lista. La búsqueda viene del menú y la categoría de la barra.
- Cada categoría tiene `icono` (Bootstrap Icons, lo elige el admin con un selector de dibujos); se ve
  solo en «Todas las categorías». Visor de fotos con fondo claro difuminado y miniaturas.
- El orden de las fotos adicionales se guarda en `FotoProducto.orden` (la principal es `Producto.imagen`).
- Detalle del producto: las fotos cambian solas cada **5 segundos** (se pausan con el mouse encima y no
  se mueven si el sistema pide «reducir movimiento»); la miniatura de la foto que se ve queda resaltada.
- **Centro de cuenta** (`templates/cuentas/_centro.html`, bloque `centro`): cabecera simple (logo,
  «Volver a la página» y menú de la cuenta, sin buscador ni barra de categorías) y menú lateral con
  Mi perfil, Datos de mi tienda (antes «Mi tienda»: datos, logo, horario y números), Seguridad,
  Ayuda y soporte, Privacidad y términos. En el celular el menú lateral es una fila de pestañas.
  En el desplegable de la cuenta, «Mi tienda» abre la **página pública** de la tienda (si está activa;
  si no, «Datos de mi tienda»).
- **Cuenta de tienda**: al iniciar sesión entra directo a «Mis productos» (salvo que viniera de un enlace
  con `?next=`; vista `cuentas.views.IngresoView`). Su menú: «Inicio», «Catálogo», «Tiendas cercanas» | «Mis productos», y en
  toda su zona de trabajo (Mis productos, crear/editar producto e inventario) no aparece la barra de categorías.
- **Mis favoritos** tiene la forma del catálogo: filtros a la izquierda (categoría con su ícono y tienda,
  varias a la vez, con su cantidad) que se aplican al hacer clic (reusa `static/js/catalogo.js`); toda la
  tarjeta abre el producto y el nombre de la tienda abre su página; «Quitar» pide confirmación.
- **Consola del administrador** (`templates/administracion/_consola.html`, bloque `consola`): al iniciar
  sesión entra directo al Resumen (`cuentas.views.destino_por_rol`). Cabecera simple (logo, etiqueta
  «Administración», «Ver página pública ↗» y su cuenta), menú lateral oscuro (Resumen, Tiendas, Productos,
  Ventas, Usuarios, Categorías, Marcas, Historial y Django Admin abajo); en el celular el menú se abre con ☰.
  No tiene Inicio/Catálogo, buscador, barra de categorías ni pie. El Resumen muestra números clave, tareas
  pendientes (tiendas por verificar y por eliminarse), gráfico de ventas de 6 meses (Chart.js, solo totales)
  y las 5 últimas acciones. `base.html` tiene los bloques `clase_body`, `clase_main`, `mensajes` y `pie`.
- **Clave temporal** (`cuentas/clave_temporal.py`, modelo `ClaveTemporal`): el admin la genera para clientes
  y tiendas activos (no para administradores) eligiendo un motivo; se muestra una sola vez, nunca se
  guarda, vence en 24 horas y queda en el Historial. Al entrar con ella, `cuentas.middleware.ClaveTemporalMiddleware`
  obliga a crear una contraseña propia (`/mi-cuenta/nueva-clave/`). Si la persona cambia su contraseña por
  otro camino, la clave temporal deja de contar (se compara la «huella»).
- **Páginas de error** (`templates/_error.html`): 403 y 404 con cabecera solo con el logo (sin buscador,
  secciones ni categorías) y una tarjeta centrada. La 403 explica a qué zona se quiso entrar
  (administración, tienda o clientes), dice con qué cuenta se entró y ofrece «Ir a Mis productos / al
  inicio / a la consola» y «Entrar con otra cuenta» (cierra sesión y vuelve al login). La 500 no usa
  plantillas ni base de datos. Ojo: con `DEBUG = True` Django muestra su propia página amarilla para el 404.
- En la tabla de Tiendas de la consola, el logo y el nombre abren el detalle (ya no hay botón «Ver»).
- **Horario del local por grupos de días** (`tiendas/forms.py`: `GruposHorarioFormSet`, `static/js/horario.js`):
  la tienda escribe un horario una vez y marca sus días (botones Lun…Dom); otro horario para días distintos;
  los días sin marcar quedan cerrados. Las horas se eligen de una lista (cada hora) o se escriben
  («8:30 a. m.», «8.30 pm», «20:30»; `leer_hora`). El refrigerio aparece solo si se marca. Resumen en vivo.
  En la base de datos sigue habiendo un `HorarioDia` por día.
- **Aviso del local** (`tiendas/_estado_local.html`): «El local (tienda física) está ABIERTO/CERRADO ahora» +
  cuándo abre o cierra; si está cerrado, aclara que en la página se pueden ver productos y escribir por
  WhatsApp a cualquier hora («te responderán en su horario»). Se usa en el perfil público y en el detalle.
- **Horario agrupado** (`Tienda.horario_agrupado`, `tiendas/_horario_agrupado.html`): días iguales juntos
  («Lunes a sábado»), mañana y tarde en líneas separadas y el día de hoy resaltado. Perfil público rediseñado.
- La tienda cambia su logo tocando el círculo del menú de la cuenta (ventana con vista previa; `tiendas:logo`).
  Se quitaron los botones «Ver mi tienda pública» (se llega con «Mi tienda» del menú de la cuenta).
- «Mis productos» y los productos del perfil público van de la A a la Z.
- «Mis productos» recuerda la página y los filtros: Editar/Eliminar llevan `?lista=…` (solo ver, q, categoria,
  marca y page) y al guardar o cancelar se vuelve ahí; la fila del producto editado se resalta (`#producto-<id>`).
  Filtro rápido «Ocultos» (no publicados u ocultos por el administrador).
- Paginación con números en todas las listas (`catalogo/_paginacion.html`, etiqueta `numeros_de_pagina`):
  todas hasta 7 páginas; con más, la primera, la última y las cercanas («1 … 8 9 10 11 12 … 30»).
- **«Publicado» y «Destacado en el inicio»** se ven como tarjetas con interruptor (verde con ojo / ámbar con
  estrella cuando están activas; textos «Sí: …» / «No: …»). Cualquier casilla de un formulario puede usarlo con
  el atributo `interruptor = {"si", "no", "icono", "icono_no", "color"}` (`_campos_formulario.html`).
  Van lado a lado (como Stock actual y Stock mínimo) con ayudas cortas: «Desmárcalo para ocultarlo sin
  eliminarlo.» y «Máximo 3 por tienda.»
- Botones de WhatsApp: el servidor arma `https://wa.me/51…?text=…` (`Tienda.enlace_whatsapp`). En el celular
  se usa así (abre la app directo en el chat). En la computadora, `static/js/whatsapp.js` (cargado en
  `base.html`) muestra al hacer clic un menú «¿Dónde abrir el chat?»: «WhatsApp Web» (`web.whatsapp.com/send`,
  pestaña nueva) o «App de WhatsApp» (`whatsapp://send`, la app de Windows si está instalada). La elección se
  puede recordar (localStorage `nexalys_whatsapp_modo`); luego sale un aviso con «Cambiar».
  No se puede reutilizar una pestaña de WhatsApp Web (probado: WhatsApp/Brave cortan el vínculo y se abre una
  nueva en cada clic), por eso se dejó la política COOP por defecto de Django (`same-origin`).
- Tabla de Mis productos (`tabla-productos`): miniatura de la foto principal (48 px, `loading="lazy"`; ícono gris
  si no tiene), encabezado en mayúsculas pequeñas, columna «Favoritos» (antes «Guardado»), estados con íconos
  (ojo Publicado, ojo tachado Oculto, estrella Destacado, Agotado, Stock bajo) y «Editar» con lápiz.
- **Menú con el mismo orden para todos**: Inicio · Catálogo · Tiendas cercanas, una línea y lo propio de cada uno
  («Mis productos», «Mis favoritos» o «Administración»).
- **Sin emojis**: todo el sitio usa íconos de línea (Bootstrap Icons): estrella, etiqueta (oferta), tienda, etc.
  El corazón de favoritos (`boton-corazon`) es blanco con borde; marcado, azul marino con corazón cian.
- **Sistema de botones** (`marca.css`): normales 46 px de alto y esquina de 12 px; `btn-sm` compactos (32 px).
  Principal `btn-primary`, Secundario `btn-outline-primary`/`-secondary` (borde azul marino), Destacado
  `btn-acento`, Peligro `btn-outline-danger` (`btn-danger` solo para confirmar), WhatsApp `btn-success`.
  Cifras de ancho fijo en tablas, notas y precios (`.precio`); texto de ayuda `--nx-texto-suave: #46566D`;
  los `.alert` llevan su ícono por CSS (✓ éxito, ! aviso, ✕ error, i información).
- Nota de venta: al imprimir sale solo la nota a hoja completa. «Anular venta» abre una ventana con lo que vuelve
  al stock, el motivo (obligatorio) y «Esta acción no se puede deshacer»; sin JavaScript sigue la página aparte.
- Catálogo: al filtrar, ordenar o cambiar de página salen **tarjetas grises de carga** (`catalogo.js`); cada foto
  de producto muestra un recuadro gris que brilla mientras carga. Pie de página completo (Explorar, Para
  tiendas, Ayuda y la franja «Proyecto IV ciclo · IESTP Urusayhua · 2026»).
- Menú «Más» de cada producto en Mis productos: `data-bs-popper-config='{"strategy":"fixed"}'` para que la tabla
  (que tiene desplazamiento propio) no lo recorte aunque haya un solo producto.
- «Agotados», «Stock bajo», el aviso amarillo del menú y las alertas del Resumen cuentan SOLO productos
  visibles; lo que no ve el cliente (oculto por la tienda o por el administrador) va solo en «Ocultos».
- **Destacados del Inicio por turnos** (`catalogo/destacados.py`): 8 lugares; primero 1 producto de cada tienda
  (su destacado más popular), luego el 2.º de cada una, etc. El orden de las tiendas rota cada día.
  «Ver todos los destacados (N)» lleva al catálogo con el filtro `destacados=on` («Destacados»).
- **Tiendas cercanas** (`/tiendas/cercanas/`, `tiendas.views.cercanas`, `templates/tiendas/cercanas.html`): para todos
  (en el menú de todos y como botón en Inicio). Mapa (OpenStreetMap) con un pin por tienda (logo o inicial) y lista: distancia, local
  abierto/cerrado, productos publicados, «Cómo llegar» (Google Maps con ruta), «Ver en el mapa», WhatsApp y
  «Ver tienda». «Usar mi ubicación» ordena por distancia (en línea recta, fórmula del haversine). Las tiendas sin
  ubicación van al final. Centro por defecto: Quillabamba (`tiendas.models.CENTRO_QUILLABAMBA`).
- **Ubicación del local**: campos `Tienda.latitud` / `Tienda.longitud` (migración `tiendas/0007_ubicacion`). La tienda
  pone el pin en «Editar datos de mi tienda» (tocar el mapa, arrastrar el pin o «Usar mi ubicación actual»).
  `Tienda.tiene_ubicacion`, `enlace_mapa()` y `enlace_como_llegar()`. El perfil público y el detalle del producto
  muestran «Cómo llegar» (y el perfil, un mapa pequeño) si la tienda marcó su local.
- Mapas: `templates/_leaflet.html` carga Leaflet y `static/js/mapas.js` (modos `data-mapa-tiendas`,
  `data-mapa-editar`, `data-mapa-tienda`). Las páginas con mapa usan el decorador `tiendas.views.con_mapa`, que
  cambia `Referrer-Policy` a `strict-origin-when-cross-origin`: OpenStreetMap exige saber el sitio y Django por
  defecto (`same-origin`) no lo envía (sin esto el mapa sale en blanco). En plantillas, las coordenadas se
  imprimen con `stringformat:'s'` o como texto, porque el formato local de Django pondría coma decimal.
  El navegador solo comparte la ubicación en https o en 127.0.0.1.
- Cada cambio va con sus pruebas (`test_*.py` en cada app). Última cuenta conocida: **593 pruebas, OK**.

## 7. Pendientes e ideas

- Publicar la página: hosting para Django (cotizado PythonAnywhere, plan Developer) y dominio .pe.
  Al publicar: **https obligatorio** (sin él no funciona «Usar mi ubicación»), `DEBUG = False`, `ALLOWED_HOSTS`,
  `SECRET_KEY` fuera del código, correo SMTP real. Si los mapas tuvieran mucho tráfico, cambiar el proveedor de
  cuadros de OpenStreetMap (una línea en `mapas.js`).
- El correo de soporte `soporte@nexalys.pe` es de demostración (`cuentas/views.py`, `CORREO_SOPORTE`).
- Los manuales del Entregable 8 se hicieron antes de: la galería única de fotos, el stock bloqueado al editar,
  el login que marca la opción correcta, el nuevo diseño del login, la galería compacta sin botones, la tabla
  de Mis productos con fotos, Tiendas cercanas, el menú con el mismo orden, los íconos sin emojis, el nuevo pie
  de página y la ventana para anular ventas. Si se actualizan, revisar esas partes y sus capturas.
- Decidir cómo cobrar a las tiendas (por ejemplo, 1 % por venta) y cómo evitar que lo evadan.
- "Seguir tiendas" (etapa 2).
- Posible migración de SQLite a MySQL más adelante.

## 8. Documentos ya hechos (en la carpeta "Claude outputs", fuera de git)

- **Entregable 8** (`Claude outputs/Entregable 8/`, entregado el 02/11/2026): Manual técnico, Manual de usuario
  (por rol, con capturas reales del entorno de demostración) y Glosario técnico bilingüe (59 términos ES–EN).
  Se generaron con un script (docx-js) en el entorno de Claude; desde ahora se editan directamente en Word.
  El índice es un campo de Word: tras cambiar algo, clic derecho > Actualizar campos > Actualizar toda la tabla.

- Plan de pruebas (F-IV-09) y plan de backup (F-IV-10).
- Valorización de costos del desarrollo (`Costos_Desarrollo_NEXALYS_Tec.docx`).
- Guía para abrir el proyecto en cada PC (`Guia_Abrir_NEXALYS.docx`).
