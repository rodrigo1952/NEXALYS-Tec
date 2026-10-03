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
| Cliente | Registro en "Registrarse" | Ver su cuenta (el catálogo es público) |

## Módulo principal: Gestionar productos (CU-03)

- **CRUD:** cada tienda crea, lista, edita y elimina sus productos.
- **Validaciones:** campos obligatorios, precio mínimo S/ 0.10, stock no negativo, imagen JPG/PNG/WEBP de máximo 2 MB, WhatsApp peruano de 9 dígitos, correo y nombre de tienda únicos.
- **Reglas de negocio:**
  1. La tienda queda **pendiente** al registrarse y se **activa sola** al verificar su correo (sin intervención del administrador).
  2. Solo las tiendas **activas** pueden gestionar productos.
  3. Una tienda **no puede ver, editar ni eliminar** productos de otra (responde 404).
  4. Una tienda no puede repetir el nombre de un producto.
  5. El catálogo público solo muestra productos **publicados** de tiendas **activas**.
  6. El administrador puede **suspender** una tienda; sus productos se ocultan y verificar el correo no la reactiva.
  7. El enlace de verificación vence a las 24 horas y no se puede falsificar (está firmado).

En desarrollo, los correos se muestran en la consola donde corre `runserver`.
