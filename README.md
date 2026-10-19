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
| Administrador | `createsuperuser` | Gestionar tiendas (suspender / reactivar), categorías, marcas y usuarios |
| Tienda | Registro en "Registrar mi tienda" + verificación del correo | Gestionar sus propios productos (CRUD) |
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

## Administración de la base de datos

- **Django Admin** (`/admin/`): consulta y gestión de todas las tablas para el Administrador.
- **DB Browser for SQLite** (https://sqlitebrowser.org): abrir el archivo `db.sqlite3` para ver la estructura de las tablas y sus registros.

En desarrollo, los correos se muestran en la consola donde corre `runserver`.
Los enlaces de verificación de tienda y de recuperación de contraseña también se imprimen completos con el prefijo `[NEXALYS]`.
