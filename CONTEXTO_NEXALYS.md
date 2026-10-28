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

- Python 3.14 (Windows), **Django 6.1.1**, SQLite (`transaction_mode` IMMEDIATE), Pillow, openpyxl.
- Bootstrap 5.3.3 y Chart.js desde CDN. Letra Space Grotesk (Google Fonts); el logo animado de Inicio usa Lilita One.
- Marca "Circuito": azul marino `#0B1B3A`, cian `#19C3E6`, fondo `#F3F6FA` (variables `--nx-*` en `static/css/marca.css`).
  Si se cambia `marca.css`, subir el número `?v=` en `templates/base.html`.
- `db.sqlite3` y `media/` **no** van a GitHub (`.gitignore`). Para llevar datos de prueba a otra PC:
  `python manage.py exportar_demo` / `python manage.py cargar_demo` (ver README).

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
- Claude no puede ejecutar Django en su entorno: revisa con `py_compile`, balance de etiquetas de
  plantillas y `node --check` para JS. **Las pruebas las corre el usuario** y manda capturas.
- Claude no puede borrar archivos en su PC; si algo sobra, le indica cuál borrar.

## 6. Convenciones del código

- Vistas: `form = Form(request.POST if request.method == "POST" else None)`.
- Operaciones de stock con `select_for_update`, bloqueando productos en orden de id. Kardex en
  `Movimiento` con cantidad con signo.
- Formsets para ventas e ingresos de varias líneas. `{% querystring %}` para filtros y paginación.
- Formularios: el atributo `fila = "inicio"/"fin"` pone dos campos en una misma fila
  (`templates/_campos_formulario.html`); `aparte = True` indica que el campo se dibuja por separado.
- Listas con buscador: un `<select>` con el atributo `data-buscable` usa `static/js/lista_buscable.js`.
- Cada cambio va con sus pruebas (`test_*.py` en cada app). Última cuenta conocida: **424 pruebas**.

## 7. Pendientes e ideas

- Publicar la página: hosting para Django (cotizado PythonAnywhere, plan Developer) y dominio .pe.
- Decidir cómo cobrar a las tiendas (por ejemplo, 1 % por venta) y cómo evitar que lo evadan.
- "Seguir tiendas" (etapa 2).
- Posible migración de SQLite a MySQL más adelante.
- Actualizar el README: la instalación debería usar `py -3.14 -m venv venv`, porque en algunas PC
  `python` abre otra versión.

## 8. Documentos ya hechos (en la carpeta "Claude outputs", fuera de git)

- Plan de pruebas (F-IV-09) y plan de backup (F-IV-10).
- Valorización de costos del desarrollo (`Costos_Desarrollo_NEXALYS_Tec.docx`).
- Guía para abrir el proyecto en cada PC (`Guia_Abrir_NEXALYS.docx`).
