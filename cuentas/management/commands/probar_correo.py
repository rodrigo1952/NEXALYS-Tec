"""
Envía un correo de prueba para revisar que el correo real (SMTP del .env) funciona.

Uso:  python manage.py probar_correo tu@correo.com
Si falla, muestra el motivo en palabras simples (clave equivocada, servidor que no responde, etc.).
"""

import smtplib
import socket

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Envía un correo de prueba con la configuración del .env (CORREO_SERVIDOR, CORREO_USUARIO, ...)."

    def add_arguments(self, parser):
        parser.add_argument("destino", help="Correo que recibirá la prueba")

    def handle(self, destino, **opciones):
        if not settings.CORREO_SERVIDOR:
            self.stdout.write(self.style.WARNING(
                "No hay CORREO_SERVIDOR en el .env: el correo se mostrará aquí abajo, no se envía de verdad."
            ))
        try:
            send_mail(
                "Prueba de correo | NEXALYS Tec",
                "Si lees esto, el correo de NEXALYS Tec funciona.",
                None,
                [destino],
            )
        except smtplib.SMTPAuthenticationError:
            raise CommandError(
                "El servidor rechazó el usuario o la clave. Con Gmail usa una «contraseña de aplicación», "
                "no la clave normal de tu cuenta."
            )
        except (socket.timeout, TimeoutError, ConnectionError, OSError) as error:
            raise CommandError(f"No se pudo conectar con {settings.CORREO_SERVIDOR}: {error}")
        except smtplib.SMTPException as error:
            raise CommandError(f"El servidor de correo respondió con un error: {error}")
        self.stdout.write(self.style.SUCCESS(f"Listo: se envió el correo de prueba a {destino}."))
