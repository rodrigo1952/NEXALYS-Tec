from django.apps import AppConfig


class CuentasConfig(AppConfig):
    name = 'cuentas'

    def ready(self):
        from . import senales  # noqa: F401  (registra las señales de la app)
