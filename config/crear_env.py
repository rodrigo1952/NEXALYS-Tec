"""
Crea el archivo .env (junto a manage.py) con una clave secreta y una dirección del Django Admin al azar.

Uso (desde la carpeta del proyecto):
    python config/crear_env.py               → .env para tu PC (DEBUG=True)
    python config/crear_env.py --produccion  → .env para el servidor (DEBUG=False); luego completa
                                               ALLOWED_HOSTS y SITIO_URL con tu dominio.

No reemplaza un .env que ya existe. La clave secreta NO se muestra en pantalla: queda solo en el archivo.
Es un script de Python común (no necesita Django), porque Django no arranca sin la clave.
"""

import secrets
import string
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO = RAIZ / ".env"

# Mismos caracteres que usa Django para sus claves (sin comillas ni espacios).
CARACTERES_CLAVE = string.ascii_lowercase + string.digits + "!@#$%^&*(-_=+)"


def clave_secreta():
    return "".join(secrets.choice(CARACTERES_CLAVE) for _ in range(50))


def ruta_admin():
    letras = string.ascii_lowercase + string.digits
    return "control-" + "".join(secrets.choice(letras) for _ in range(12)) + "/"


def contenido(produccion=False):
    if produccion:
        sitio = (
            "# Dominio del sitio (sin / al final). Se usa en los enlaces que se comparten por WhatsApp.\n"
            "ALLOWED_HOSTS=tu-usuario.pythonanywhere.com\n"
            "SITIO_URL=https://tu-usuario.pythonanywhere.com\n"
            "# En PythonAnywhere la IP real del visitante llega en esta cabecera.\n"
            "IP_CABECERA=HTTP_X_REAL_IP\n"
        )
    else:
        sitio = (
            "ALLOWED_HOSTS=localhost,127.0.0.1\n"
            "SITIO_URL=http://127.0.0.1:8000\n"
        )
    return (
        "# Datos secretos de NEXALYS Tec. NO subir a GitHub (ya está en .gitignore).\n"
        "# Explicación de cada dato: .env.example\n"
        f"SECRET_KEY={clave_secreta()}\n"
        f"DEBUG={'False' if produccion else 'True'}\n"
        f"DJANGO_ADMIN_URL={ruta_admin()}\n"
        + sitio
    )


def main():
    if ARCHIVO.exists():
        print(f"Ya existe {ARCHIVO}. No se cambió nada (bórralo primero si quieres uno nuevo).")
        return 1
    produccion = "--produccion" in sys.argv
    texto = contenido(produccion)
    ARCHIVO.write_text(texto, encoding="utf-8")
    admin = next(l.split("=", 1)[1] for l in texto.splitlines() if l.startswith("DJANGO_ADMIN_URL="))
    print(f"Listo: se creó {ARCHIVO} con una clave secreta nueva (no se muestra).")
    print(f"Django Admin en: /{admin}")
    if produccion:
        print("Ahora cambia ALLOWED_HOSTS y SITIO_URL por tu dominio real.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
