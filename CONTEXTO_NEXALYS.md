# Contexto de NEXALYS Tec (para continuar en un chat nuevo)

> **Para Claude:** lee este archivo completo antes de empezar. Resume el proyecto, cómo trabajamos
> y lo que está pendiente. El código del repositorio es la fuente de verdad: si algo de aquí no
> coincide con el código, manda el código (y avisa al usuario).

## 1. Qué es el proyecto

- **NEXALYS Tec**: marketplace web donde las tiendas de tecnología de **Quillabamba** publican sus
  productos y los clientes los encuentran y contactan a la tienda por **WhatsApp** (no hay pago en línea).
- Proyecto de curso del IV ciclo (IESPP Urusayhua). Empresa del caso: Logical Center S.R.L.
- Repositorio (público): https://github.com/rodrigo1952/NEXALYS-Tec.git — rama `main`.
- Estado: funciona en local (aún no publicada). Plan: promocionarla de tienda en tienda y luego
  publicarla (hosting para Django + dominio .pe).

## 2. Tecnología

- Python 3.14 (Windows; el venv se crea con `py -3.14 -m venv venv` y VS Code usa ese intérprete), **Django 6.1.1**, SQLite (`transaction_mode` IMMEDIATE), Pillow, openpyxl.
- Bootstrap 5.3.3 y Chart.js desde CDN. Letra Space Grotesk (Google Fonts); el logo animado de Inicio usa Lilita One.
- Marca "Circuito": azul marino `#0B1B3A`, cian `#19C3E6`, fondo `#F3F6FA` (variables `--nx-*` en `static/css/marca.css`).
  Si se cambia `marca.css`, subir el número `?v=` en `templates/base.html`.
- `db.sqlite3`, `media/` y `.vscode/` **no** van a GitHub (`.gitignore`). Para llevar datos de prueba a otra PC:
  `python manage.py exportar_demo` / `python manage.py cargar_demo` (ver README).
- Para la presentación: `python manage.py cargar_productos_presentacion` crea 3 tiendas ficticias
  (Selva Byte, Valle Digital Tech, Kantu Tech; WhatsApp del equipo 930909090, 920909090, 910909090)
  con 47 productos reales sin foto (datos en `catalogo/presentacion.py`; enlaces para las fotos en
  "Claude outputs/Fotos_productos_presentacion.md").

## 3. Roles y módulos

- **Visitante**: ve el catálogo sin registrarse.
- **Cliente**: favoritos con avisos dentro de la página (sin correo). No hay reseñas.
- **Tienda**: se registra como "pendiente" y se activa al confirmar su correo. Gestiona productos
  (varias fotos, ofertas con fecha fin opcional, hasta 3 destacados), perfil con horario por día,
  logo, dirección y Google Maps. Inventario completo:
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
- **Datos sensibles**: cambiar nombre, apellido o correo de la cuenta, y nombre, dirección o WhatsApp
  de la tienda, pide la contraseña otra vez (`cuentas/reautenticacion.py`, válido 10 minutos).
  Los productos no la piden.
- **Login**: el selector "Soy cliente / Soy tienda" se valida. Una tienda debe entrar como tienda y
  un cliente como cliente; el administrador entra con cualquiera. El aviso solo sale si la contraseña
  es correcta.
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
- Fotos al editar un producto (`catalogo/_galeria_edicion.html`): principal grande a la izquierda y
  adicionales más pequeñas; se arrastra una adicional a la principal para intercambiarlas, se sueltan
  archivos sobre una foto para reemplazarla o en la galería para agregarlos; la «X» marca para quitar
  (con Deshacer). Todo se aplica al «Guardar». Visor de fotos con flechas, teclado y contador en
  `static/js/visor.js` (las imágenes con el mismo `data-galeria` se recorren juntas).
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
- Galería al editar: «Hacer principal» o arrastrar una adicional a la principal las intercambia en la
  pantalla al instante (arrastrarla de vuelta lo deshace); un archivo de la PC reemplaza.
  La principal también se puede arrastrar sobre una adicional: se intercambian igual.
  Arrastrar una adicional sobre otra adicional las **cambia de lugar** (con «Deshacer orden»); cada foto
  muestra un número con el orden en que la ve el cliente (1 = principal). El orden viaja en el campo
  oculto `orden_fotos` y se guarda en `FotoProducto.orden` (`ProductoForm.ordenar_fotos`).
- Detalle del producto: las fotos cambian solas cada **5 segundos** (se pausan con el mouse encima y no
  se mueven si el sistema pide «reducir movimiento»); la miniatura de la foto que se ve queda resaltada.
- **Centro de cuenta** (`templates/cuentas/_centro.html`, bloque `centro`): cabecera simple (logo,
  «Volver a la página» y menú de la cuenta, sin buscador ni barra de categorías) y menú lateral con
  Mi perfil, Datos de mi tienda (antes «Mi tienda»: datos, logo, horario y números), Seguridad,
  Ayuda y soporte, Privacidad y términos. En el celular el menú lateral es una fila de pestañas.
  En el desplegable de la cuenta, «Mi tienda» abre la **página pública** de la tienda (si está activa;
  si no, «Datos de mi tienda»).
- **Cuenta de tienda**: al iniciar sesión entra directo a «Mis productos» (salvo que viniera de un enlace
  con `?next=`; vista `cuentas.views.IngresoView`). Su menú es «Mis productos», «Inicio», «Catálogo», y en
  toda su zona de trabajo (Mis productos, crear/editar producto e inventario) no aparece la barra de categorías.
- **Mis favoritos** tiene la forma del catálogo: filtros a la izquierda (categoría con su ícono y tienda,
  varias a la vez, con su cantidad) que se aplican al hacer clic (reusa `static/js/catalogo.js`); toda la
  tarjeta abre el producto y el nombre de la tienda abre su página; «Quitar» pide confirmación.
- Cada cambio va con sus pruebas (`test_*.py` en cada app). Última cuenta conocida: **494 pruebas**.

## 7. Pendientes e ideas

- Publicar la página: hosting para Django (cotizado PythonAnywhere, plan Developer) y dominio .pe.
- Decidir cómo cobrar a las tiendas (por ejemplo, 1 % por venta) y cómo evitar que lo evadan.
- "Seguir tiendas" (etapa 2).
- Posible migración de SQLite a MySQL más adelante.

## 8. Documentos ya hechos (en la carpeta "Claude outputs", fuera de git)

- Plan de pruebas (F-IV-09) y plan de backup (F-IV-10).
- Valorización de costos del desarrollo (`Costos_Desarrollo_NEXALYS_Tec.docx`).
- Guía para abrir el proyecto en cada PC (`Guia_Abrir_NEXALYS.docx`).
