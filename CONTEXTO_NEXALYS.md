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
- Bootstrap 5.3.3, Bootstrap Icons 1.11.3, Chart.js 4.4.1, **Leaflet 1.9.4** y las letras Space Grotesk y Lilita One
  están **dentro del proyecto** en `static/vendor/` (LEEME.md con versiones y licencias; sin `sourceMappingURL`).
  Ningún CDN: solo los cuadros del mapa vienen de **OpenStreetMap** (y, al marcar el local, las fotos satelitales de
  **Esri** y la búsqueda de calles de **Nominatim**; los tres están permitidos en `SECURE_CSP`). Se descargaron con
  `Claude outputs/descargar_librerias.ps1`. QR con **segno 1.6.6** (en requirements).
- Marca "Circuito": azul marino `#0B1B3A`, cian `#19C3E6` (variables `--nx-*` en `static/css/marca.css`).
- **Diseño celeste** (nov 2026; reemplazó por completo a «Carbón y oro», también en la consola del administrador y en
  los correos, a pedido del usuario el 17 nov).
  Se aplica por fases y el usuario revisa cada una: 1) estilos base, cabecera, pie e Inicio (HECHA, falta su revisión);
  2) Catálogo y Detalle; 3) Perfil de la tienda y Tiendas cercanas; 4) Login, Registro y Cuenta; 5) Favoritos;
  6) Mis productos (Resumen, Productos, Ventas, Editar). La vista previa aprobada está en el lienzo de diseño
  «NEXALYS Tec — Vista previa del diseño celeste» y en `Claude outputs/NEXALYS_Tec_Diseno_Celeste.pdf`.
  CSS: sección **100** de `marca.css` (todas sus reglas llevan delante `body.fondo-marca`, así ganan a las de antes).
  «Carbón y oro» ya no existe (`static/img/fondo-vetas.svg` quedó sin uso).
  **Consola del administrador**: cabecera clara con el logo en cuadro azul y la etiqueta «Administración» celeste, menú
  lateral de vidrio (flotante, esquinas de 22 px) con la sección elegida en una píldora azul, cifras, paneles y tablas
  en cajas blancas o de vidrio; gráfico de ventas con el mes actual en azul y los anteriores en celeste.
  **Correos** (`templates/correos/base.html`, `_boton`, `_codigo`, `_respaldo`): fondo celeste, franja azul con degradado
  (`bgcolor` azul liso para Outlook), logo dibujado con una tabla (cuadrito azul marino con la «N» y borde cian, sin
  imagen), tarjeta blanca con esquinas de 18 px, botón azul, código en un recuadro celeste; letra Arial. Fondo celeste muy claro
  con manchas suaves (`.fondo-marca::before/::after`), tarjetas blancas y paneles de vidrio (`.panel-vidrio`: blanco
  translúcido con desenfoque), botones azules con degradado (`--cel-grad`), esquinas de 14 a 22 px. Títulos y precios
  en Space Grotesk; textos en **Inter** (`static/vendor/fuentes/inter-400/500/600/700.woff`, reducida a letras latinas).
  Variables `--cel-*`. El fondo de la página es contexto CLARO; las cajas oscuras (franja del Inicio, cabecera del menú
  del celular) usan `contexto-oscuro`. Botones nuevos: `btn-claro` (celeste suave), `btn-wa` (WhatsApp suave),
  `btn-wa-borde` (¿Cuándo llega?) y `btn-pildora` («Ver todos … →»). Logo: `{% include "_logo.html" with caja=True %}`
  (la N blanca en un cuadro azul con degradado; «Tec» en azul, sin punto) en la cabecera y el pie.
  **Cabecera**: logo, buscador blanco redondeado con lupa y botón «Buscar», corazón con la cantidad (cliente) y la cuenta
  en una píldora blanca; el visitante ve un círculo con la persona y, en la segunda fila a la derecha, «Iniciar sesión»,
  «Registrarse» y «Registrar mi tienda» (`.menu-acceso`). Secciones con íconos (casa, cuadrícula, ubicación); la elegida
  en una píldora blanca con texto azul. Barra de categorías en píldoras suaves.
  **Tarjeta de producto** (`catalogo/_tarjeta_producto.html`): etiqueta de la marca con su color
  (`chip-marca--<marca con slugify>`, colores en marca.css; las demás en azul marino), descuento «-20%» sobre la foto,
  precio grande en azul con el anterior tachado delante, tienda y botón «Consultar por WhatsApp» (en el celular solo
  «WhatsApp»; agotado: «¿Cuándo llega?» con borde verde y la foto más clara). El botón está por encima del enlace que
  cubre la tarjeta (z-index 2).
  **Inicio** (como la vista previa): panel de Categorías (primero), «¿Qué tienda está abierta ahora?» con la fecha y
  hora de Perú debajo («Martes 17 de noviembre · 6:52 p. m.», `tiendas.inicio.fecha_y_hora`), «Usar mi ubicación» y
  «Ver todas las tiendas (N) →»; tarjetas de tienda de vidrio, 3 por fila: logo (o inicial en un círculo de color según
  el último dígito del id, `tienda-inicio__logo--c0…c9`), nombre, estado con punto verde/ámbar, etiquetas, 3 productos
  con precio y la dirección abajo; toda la tarjeta lleva al perfil. Luego destacados, ofertas y recientes con
  píldoras «Ver todos…», «Así funciona NEXALYS Tec» (Busca · Compara · Escribe por WhatsApp) y la franja azul
  «¿Tienes una tienda de tecnología en Quillabamba?» (no la ven las tiendas ni el administrador).
- **Lo que hace distinta a cada tienda** (`tiendas/etiquetas.py`, migración `tiendas/0009`): frase corta `lema`
  (30 letras, azul con borde), servicios que marca la tienda en «Editar datos» (`repara_celulares`, `repara_computadoras`,
  `instala_camaras_redes`, `impresoras_tintas` + `otro_servicio` de texto libre, 40 letras; celeste) y
  **especialidades automáticas** (grises): categorías con ≥ 2 productos publicados y ≥ 30 % de su catálogo, máx. 2,
  sin «Otros». Se ven en el Inicio (máx. 3), en el perfil, en «Datos de mi tienda» y en Tiendas cercanas, que tiene
  filtros `?servicio=<campo>` y `?especialidad=<id de categoría>` (solo aparecen los que alguna tienda tiene).
  Pie blanco translúcido con el logo y 4 columnas (2 en el celular): marca, Explorar, Para tiendas y Contacto (correo
  `CORREO_SOPORTE`, Ayuda, Privacidad y términos, Libro de Reclamaciones). Al imprimir, hoja blanca.
  **No se escribe `?v=` a mano**: en tu PC (DEBUG=True) `config/estaticos.py` (EstaticosConVersion) agrega solo
  `?v=<fecha del archivo>`; en el servidor `ManifestStaticFilesStorage` + `collectstatic` ponen la huella al nombre
  (`STATIC_ROOT = staticfiles/`, fuera de git). `requirements.txt` con versiones exactas (pillow 12.3.0, openpyxl 3.1.5).
  Tarjetas, campos de formulario y **filas de todas las tablas en blanco** en todo el sitio (el fondo de la página
  es celeste muy claro); al enfocar un campo, borde y brillo azul; al pasar el mouse por una fila, celeste muy suave.
- **Datos secretos en `.env`** (junto a `manage.py`, NO va a GitHub; modelo en `.env.example`, lo lee
  `config/entorno.py`). Lo crea `python config/crear_env.py` (o `--produccion`). Datos: `SECRET_KEY`, `DEBUG`
  (si falta = False), `ALLOWED_HOSTS`, `SITIO_URL` (enlaces completos para compartir), `DJANGO_ADMIN_URL`
  (Django Admin en dirección secreta; su /login/ redirige al login de la página), `IP_CABECERA`
  (PythonAnywhere: `HTTP_X_REAL_IP`), y con DEBUG=False: `COOKIES_SEGURAS`, `HSTS_SEGUNDOS`, `PROXY_HTTPS`,
  `FORZAR_HTTPS`. Nunca escribir ni mostrar la SECRET_KEY. `check --deploy` solo marca el correo de consola.
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
- El módulo "Pedidos" se retiró (sus pedidos se convirtieron en ventas) y la app `pedidos` se quitó del proyecto.
  La migración inventario 0004 quedó vacía (solo mantiene el orden) y la 0005 borra sus restos en la base de datos.

## 4. Reglas que NO se deben romper

- **Privacidad por tienda**: costos, ganancia, proveedores y clientes de cada tienda solo los ve esa
  tienda. El administrador no los ve.
- **Datos sensibles**: cambiar nombre, apellido o correo de la cuenta, y nombre, dirección, WhatsApp o
  **ubicación en el mapa** de la tienda, pide la contraseña otra vez (`cuentas/reautenticacion.py`, válido
  10 minutos). Los productos no la piden. La caja de la contraseña va encima de «Guardar cambios»
  (`templates/_confirmar_clave.html`, nov 2026) y `static/js/formularios.js` la muestra apenas cambia un dato
  sensible, con el motivo («Cambiaste: ubicación en el mapa»); si se intenta guardar sin ella, no se envía y la
  resalta. Cada campo sensible lleva `data-sensible`, `data-sensible-tipo` y `data-sensible-original`.
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
  «Ordenar por» (`favoritos/views.py → ordenar()`, se recuerda en `PreferenciaFavoritos`): **Recomendado**
  (por defecto) = 1) bajaron de precio desde que se guardaron, 2) volvieron a tener stock en los últimos 7 días
  (`Producto.repuesto_el`, se anota en `Producto.save()` al pasar de 0 a más), 3) los demás, 4) agotados o
  no disponibles; dentro de cada grupo, el último agregado primero. Otros: Agregados recientemente, Nombre
  (A-Z), Precio menor/mayor, Mayor descuento (los agotados y no disponibles siempre al final). La rebaja se
  muestra como «Bajó S/ X desde que lo guardaste» (ya no hay un tercer precio tachado).
  **Agotado ≠ No disponible**: «No disponible» (producto oculto o tienda suspendida) quita WhatsApp; «Agotado»
  (tienda activa, stock 0) aclara la foto y cambia el botón por «¿Cuándo llega?» (borde verde; «Preguntar cuándo llega» en el detalle), también
  en la página del producto; `Producto.mensaje_whatsapp()` pregunta cuándo vuelve a tener stock.
  «No disponible» explica: «La tienda ya no lo tiene publicado…» (+ «Ver tienda») o «Esta tienda no está
  disponible por ahora…» (tienda suspendida); nunca dice si lo ocultó el administrador. Si vuelve a publicarse
  (`Producto.republicado_el`: la tienda lo publica, el admin deja de ocultarlo o `Tienda.reactivar()`), sale
  «Volvió a estar disponible» y sube al grupo 2 durante 7 días.
- **WhatsApp en la computadora** (`static/js/whatsapp.js`): «Recordar mi elección» viene desmarcado; el aviso
  de abajo dura 15 s (se pausa con el mouse encima) y su «Cambiar» es un botón; en el producto y la tienda,
  bajo los botones (y arriba de la lista en Mis favoritos y Tiendas cercanas), `[data-modo-whatsapp]` muestra
  «El chat se abre en WhatsApp Web · Cambiar».
- **Mensajes de WhatsApp** (`catalogo/whatsapp.py`; en plantillas `{% load whatsapp %}` →
  `{% whatsapp_producto producto %}` / `{% whatsapp_tienda tienda %}`): saludo según la hora de Perú (Buenos días
  5–11:59, Buenas tardes 12–18:59, Buenas noches), «Soy <primer nombre>.» si inició sesión, producto en *negrita*
  con «Precio:», «¿Sigue disponible? ¿Cómo puedo comprarlo?» (agotado: «¿Saben cuándo vuelve a tener stock?») y el
  enlace al final. Tienda y Tiendas cercanas: «Encontré su tienda en NEXALYS Tec y quisiera hacerles una consulta.»
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
  El título de la nota y del ingreso empieza con la tienda («Selva Byte - Nota de venta N.° 00007»): es el nombre
  del PDF al «Guardar como PDF» (nov 2026).
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
  Ayudas (nov 2026, `mapas.js`): «Buscar» una calle de Quillabamba (Nominatim: una búsqueda por clic, sin
  autocompletar, máx. 1 por segundo, dentro de ~9 km), botones «Mapa / Satélite» (Esri World Imagery + calles) y
  «Ampliar mapa» (pantalla completa dentro de la página; «Reducir mapa» arriba, el botón ⤢/⤡ en la esquina del
  mapa o Esc lo devuelven). «Buscar» cambia «Jr./Av./Psje./Ca./Prol./Urb.» por la palabra completa, quita el
  número de puerta y, si no encuentra nada, prueba solo con el nombre de la calle (1,1 s después).
- **Logo de la tienda** (`templates/tiendas/_campo_logo.html` + `static/js/campo_logo.js`): círculo grande como
  las fotos de los productos (clic o arrastrar, vista previa, «Quitar logo», «Deshacer»). Se usa en «Editar datos
  de mi tienda» (el campo `logo` va `aparte`; quitar = casilla `datos-logo-clear`) y en la ventana del círculo del
  menú de la cuenta (`tiendas:logo`; «Guardar logo» se activa al elegir una imagen).
  `Tienda.tiene_ubicacion`, `enlace_mapa()` y `enlace_como_llegar()`. El perfil público y el detalle del producto
  muestran «Cómo llegar» (y el perfil, un mapa pequeño) si la tienda marcó su local.
- Mapas: `templates/_leaflet.html` carga Leaflet y `static/js/mapas.js` (modos `data-mapa-tiendas`,
  `data-mapa-editar`, `data-mapa-tienda`). Las páginas con mapa usan el decorador `tiendas.views.con_mapa`, que
  cambia `Referrer-Policy` a `strict-origin-when-cross-origin`: OpenStreetMap exige saber el sitio y Django por
  defecto (`same-origin`) no lo envía (sin esto el mapa sale en blanco). En plantillas, las coordenadas se
  imprimen con `stringformat:'s'` o como texto, porque el formato local de Django pondría coma decimal.
  El navegador solo comparte la ubicación en https o en 127.0.0.1.
- Límite de intentos (`cuentas/limites.py`, modelo `IntentoAcceso`, migración 0005): login 5 claves
  equivocadas usuario+IP → 15 min (20 por IP); correos (confirmación, verificación de tienda, recuperar
  contraseña) 3 por hora (10 por IP). Mensaje «Demasiados intentos. Vuelve a intentarlo en N minutos».
- Miniaturas: filtro `{% load miniaturas %}` `|miniatura` (600 px webp), `|miniatura:'icono'` (160 px),
  `|miniatura:'compartir'` (JPEG 600 px para og:image). Se crean al pedirlas en `media/miniaturas/<tipo>/` y el
  almacenamiento `catalogo.almacenamiento.AlmacenamientoConMiniaturas` las borra con la original. Comando
  `crear_miniaturas`. El detalle grande y el admin siguen con la foto original.
- Compartir: `Producto/Tienda.get_absolute_url()` y `enlace_publico()` (SITIO_URL); mensaje de WhatsApp con el
  enlace al final; etiquetas Open Graph en `base.html` (bloques `descripcion` y `vista_previa`), producto y
  tienda; botón `templates/_compartir.html` + `static/js/compartir.js` (táctil → menú del teléfono; PC → copia).
- **CSP** (`SECURE_CSP` en settings, middleware de Django 6): todo `<script>` en plantilla lleva `{% csp_nonce_attr %}`;
  prohibido `onclick=`/`onchange=` (usar `data-imprimir`, `data-enviar-al-cambiar` o addEventListener). Comentarios
  `{# #}` solo de UNA línea (si no, el texto sale en la página; hay prueba).
- **Aviso de errores**: `administracion/registro_errores.py` (handler en LOGGING de `django.request`) guarda cada 500
  en `ErrorRegistrado` (agrupados por firma, máx. 300); consola Control → Errores, globo y tarea en el Resumen;
  correo a `ADMINS` (`CORREO_ADMIN` del .env) cuando haya SMTP.
- **Privacidad Ley 29733**: `cuentas/privacidad.py` (`VERSION_POLITICA` = 2026-11-11, plazos 8/20/10 días hábiles),
  modelos `ConsentimientoPrivacidad` y `SolicitudDerecho` (migración cuentas 0006), casilla `acepto_privacidad` en
  ambos registros, `PrivacidadMiddleware` (aceptar al entrar; admin exento; las pruebas lo apagan con
  `config/pruebas.py`), `/privacidad/aceptar/`, `/privacidad/solicitud/`, `/mi-cuenta/mis-datos/` (página legible para guardar en PDF; copia técnica
  en `/mi-cuenta/mis-datos/copia.json`, nov 2026), consola
  Control → Privacidad (responder envía correo y queda en el historial). Datos del responsable en el .env
  (`PRIVACIDAD_*`); mientras falten: «por completar» en la política y tarea en el Resumen.
- **Correo real**: `MAILERS` SMTP si hay `CORREO_SERVIDOR` en el .env (Gmail + contraseña de aplicación; puerto 587
  TLS; `CORREO_REMITENTE`); si no, consola. Prueba: `python manage.py probar_correo correo@x.com`.
- **Copias de seguridad**: `administracion/copias.py` (backup de SQLite + media sin miniaturas en zip, carpeta `copias/`
  fuera de git, 14 días, nunca borra la última); comandos `copia_seguridad` y `restaurar_copia --confirmar`; consola
  Control → Copias de seguridad (crear y descargar). Sus pruebas usan TransactionTestCase (SQLite no copia con una
  transacción abierta).
- **Libro de Reclamaciones**: app `reclamos` (modelo `Reclamo`, correlativo por proveedor y año «000001-2026»,
  datos del proveedor copiados en la hoja, 15 días hábiles, constancia por correo, aviso a la tienda). URLs en
  `/libro-de-reclamaciones/` (público, `hoja/<pk>/`, `mi-tienda/` para la tienda, `consola/` para el admin). La tienda
  responde las suyas; el admin responde las de NEXALYS o de una tienda eliminada. Enlace en el pie y en la página de
  la tienda. `Tienda.ruc` (opcional, migración tiendas 0008).
- **QR de la tienda**: `tiendas/qr.py` (segno, corrección Q), `/tiendas/panel/qr/` cartel para imprimir y
  `/tiendas/panel/qr.png|svg`. Solo tiendas activas.
- **«Mi código QR» de la tienda (nov 2026)**: ítem propio en el menú lateral del centro de cuenta, en el menú del
  avatar y en el menú del celular (solo tiendas activas); ya no hay tarjeta del QR en «Datos de mi tienda». La página
  (`/tiendas/panel/qr/`, Propuesta A) muestra arriba los escaneos (este mes con la comparación con el mes pasado, total
  y último) y debajo el cartel con el panel de compartir/descargar. El QR lleva `…/tiendas/<pk>/?desde=qr`: `perfil`
  cuenta el escaneo (`EscaneoQR`: tienda + fecha; migración tiendas 0010) una vez por visita (sesión), sin contar a la
  propia tienda ni al administrador, y redirige a la página limpia. El enlace que se comparte va sin la marca.
- **Formularios con errores (nov 2026)**: `static/js/formularios.js` (en `base.html`) baja hasta el primer error y lo
  resalta (`.campo-resaltado`) cuando la página es la respuesta a un POST (`<body data-formulario-enviado>`).
- **Pin del mapa (Editar mi tienda, nov 2026)**: si queda distinto de lo guardado (`data-guardada-lat/lng`), sale el
  aviso «Moviste el pin» / «Quitaste tu local del mapa» con «Deshacer» (`.aviso-pin`), porque un toque lo mueve.
- **QR de la página (feria, nov 2026)**: `administracion/qr.py` (segno, corrección Q). Consola → General → «QR de la página»
  (`/administracion/qr/`): cartel para imprimir (mismas clases y `cartel_qr.js` que el de las tiendas), descargas
  `/administracion/qr.png|svg`, contador de visitas y «Abrir pantalla para la feria» (`/administracion/qr/pantalla/`,
  sin cabecera ni pie, QR grande; el contador se actualiza cada 15 s con `/administracion/qr/visitas/`). El QR lleva a
  `SITIO_URL/?desde=qr`: `inicio` (cuentas/views.py) cuenta la visita (`VisitaQR`, solo la fecha; migración
  administracion 0007) una vez por sesión, no cuenta al administrador y redirige al Inicio limpio. «Poner el contador
  en cero» (POST). Como el enlace del túnel cambia, el QR no se guarda: se arma al abrir la página.
- **Duplicar producto**: `catalogo:crear?copiar=<pk>` abre el formulario lleno (`_datos_para_duplicar` en
  catalogo/views.py): todo menos stock (0), fotos y código interno; sin publicar ni destacar; la oferta solo si
  sigue vigente y la categoría/marca solo si siguen activas. Solo productos de la misma tienda (404 si no).
  Enlace en «Más» de Mis productos y botón «Duplicar» al editar.
- **Compartir** (`static/js/compartir.js`): ventanita «Compartir en…» con WhatsApp (en la PC respeta la elección Web/App
  de whatsapp.js), Facebook (sharer.php), X (twitter.com/intent/tweet), Telegram (t.me/share/url), Correo (mailto) y
  Copiar enlace; «Más opciones» (navigator.share) solo si el navegador lo tiene. En el celular sale desde abajo
  (`.menu-compartir--abajo`) con «Cancelar». TikTok e Instagram no tienen enlace web para compartir.
- **Precio en ingresos**: el costo se promedia (promedio ponderado) y el precio de venta NO cambia solo (un solo precio
  por producto). En Nuevo ingreso, bajo cada línea, se ve el costo promedio nuevo y la ganancia por unidad (rojo si no
  gana) y un campo opcional «Nuevo precio de venta» (`precio_venta` en LineaIngresoForm; si está en oferta, debe ser
  mayor que la oferta). Queda anotado en `LineaIngreso.precio_anterior/precio_nuevo` (migración inventario 0006) y se
  ve en el detalle; anular el ingreso NO devuelve el precio (se avisa). Al guardar, `servicios.ventas_sin_ganancia`
  avisa los productos que quedan con precio ≤ costo.
- **Login**: desde el 1.er error dice cuántos intentos quedan (`limites.intentos_restantes`, la regla más cercana) y
  enlaza «¿Olvidaste tu contraseña?». Avisos (`.alert`) en todo el sitio: tarjeta blanca, borde izquierdo de color,
  ícono en círculo (`--alerta-color`, `--alerta-fondo`) y texto azul marino.
- **El .env manda** (`config/entorno.py` reemplaza valores ya puestos: VS Code copia el .env a la terminal al abrirla).
  `NEXALYS_SIN_ENV=1` evita leerlo (pruebas que arrancan Django como en el servidor).
- **Detalles de errores solo en tu PC** (`config/middleware.py`, primero en MIDDLEWARE): con DEBUG=True, si la visita
  no es de localhost/127.0.0.1 (túnel de Cloudflare, celular por Wi-Fi), la página amarilla se cambia por 404/403/500.
- **Mostrar la página sin publicarla**: túnel de Cloudflare (`cloudflared tunnel --url http://localhost:8000`, enlace
  `https://…trycloudflare.com` que cambia cada vez; en el .env `ALLOWED_HOSTS` con `.trycloudflare.com` y `SITIO_URL` = el enlace).
- **Celular (nov 2026)**: menú lateral `templates/_menu_movil.html` (offcanvas `#menu-movil`, ☰ a la izquierda; cuenta
  arriba con «Iniciar sesión»/«Crear cuenta» o el usuario; secciones con íconos, categorías, ayuda, «Cerrar sesión»).
  Cabecera más baja en < 992 px. Inicio: fila de categorías con íconos y 2 productos por fila. Catálogo: barra
  «Filtrar | Ordenar» fija (`top: var(--cabecera-visible)`, la pone el script de la cabecera), rangos rápidos de
  precio (`RANGOS_PRECIO` y `_rangos_precio` en catalogo/views.py) y «Precio» primero en Filtrar. Mis productos:
  en < 992 px la tabla se ve como tarjetas (solo CSS; 2 por fila en tableta). La computadora casi no cambia.
- **Correos** (`config/correos.py`): `enviar(destinos, asunto, "app/plantilla", contexto, vista_previa=…)` usa
  `plantilla.html` (extiende `correos/base.html`, estilos en línea, Arial) + `plantilla.txt`; `reply_to` =
  `CORREO_RESPUESTAS` (= CORREO_SOPORTE solo si está en el .env). `enlace(ruta)` arma con SITIO_URL;
  `vence_en_palabras(horas)` → «el lunes 16 de noviembre a las 5:24 p. m.». Todos los correos lo usan
  (confirmación, bienvenida cliente/tienda, verificación tienda, recuperar contraseña, Libro, solicitudes, prueba).
- **Código de 6 dígitos** (`cuentas/codigos.py`, modelo `CodigoVerificacion`, migración cuentas 0007): solo la
  huella HMAC; uno nuevo reemplaza al anterior; vence como el enlace. Vistas `confirmar_codigo` (cliente) y
  `tiendas:verificar_codigo` (panel). Límite `limites.CODIGO`: 5 equivocados cada 15 min.
- **No perder lo escrito** (nov 2026): `static/js/no_perder.js` (cargado en `base.html`, al final):
  `<form data-avisar-salida>` pregunta antes de salir si hubo cambios (producto, editar tienda, ingreso, venta,
  ajuste, conteo, proveedor, hoja y respuestas de reclamos); `data-borrador="<nombre>-u<id>"` guarda un borrador
  en localStorage (3 días) con aviso «Recuperar / Descartar» (ingreso, venta, ajuste y conteo; el conteo usa
  `data-borrador-mezclar` para no borrar lo contado en otras categorías); `<a data-guardar-borrador>` («+ Crear
  producto») guarda y al volver recupera sin preguntar. `static/js/lineas_productos.js` (`data-lineas`/`data-linea`):
  si se elige un producto repetido suma la cantidad en su fila; al volver con `?producto=ID` lo pone en la primera
  fila libre. El servidor rechaza el mismo producto en dos filas (`inventario/forms.py`, `BaseLineas.clean`).
  «+ Nuevo proveedor» en el ingreso abre una ventanita que llama a `inventario:proveedor_rapido` (POST, JSON,
  prefijo `proveedor-`) y deja al proveedor elegido.
- **Mis productos**: los destacados van primero (`order_by("-destacado", Lower("nombre"), "pk")`) con fondo cian
  suave, línea cian (`fila-producto--destacada`), ★ cian oscuro y etiqueta «Destacado» azul marino (`etiqueta-destacado`).
- **QR de la tienda**: cartel a la izquierda y panel al lado (`pagina-cartel` / `panel-cartel`; en el celular, debajo)
  con COMPARTIR e IMPRIMIR Y DESCARGAR. `static/js/cartel_qr.js` dibuja el cartel en un PNG de 1080×1350 (al cargar
  la página) y según `data-compartir-red`: en el celular usa `navigator.share({files})`; en la PC, WhatsApp copia
  la imagen (ClipboardItem) y abre WhatsApp Web (o la app) para pegarla con Ctrl+V, Facebook abre el sharer con el
  enlace y deja la imagen copiada, Instagram descarga y abre instagram.com; «Más» = menú del sistema con la imagen
  o, si no se puede, la ventana de `_compartir.html` (acepta `etiqueta`, `icono` y `red`).
- Cada cambio va con sus pruebas (`test_*.py` en cada app). Última cuenta conocida: **868 pruebas, OK** (antes del
  diseño celeste; sus pruebas están en `cuentas/test_celeste.py`, que reemplazó a `cuentas/test_carbon_oro.py`).
  Tras la fase 1: 878 pruebas, todas bien salvo una prueba nueva (ya corregida).

## 7. Pendientes e ideas

- Publicar la página: hosting para Django (cotizado PythonAnywhere, plan Developer) y dominio .pe.
  Al publicar: **https obligatorio** (sin él no funciona «Usar mi ubicación»), `.env` de producción
  (`python config/crear_env.py --produccion`), Force HTTPS en PythonAnywhere, correo SMTP real,
  `collectstatic` y mapeo /static/ y /media/ en la pestaña Web. Trámites del usuario: inscribir el banco de datos
  en el Registro Nacional de Protección de Datos Personales (gratis) y declarar el flujo transfronterizo si el
  servidor está fuera del Perú. Si los mapas tuvieran mucho tráfico, cambiar el proveedor de
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
