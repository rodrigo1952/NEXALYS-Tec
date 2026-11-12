"""
Ejecutor de pruebas de NEXALYS (TEST_RUNNER en config/settings.py).

Apaga «aceptar la política de privacidad al entrar» en todas las pruebas, porque casi todas
inician sesión con cuentas creadas a mano (sin pasar por el registro). Las pruebas de esa regla
la vuelven a encender con @override_settings(PRIVACIDAD_OBLIGATORIA=True) (cuentas/test_privacidad.py).
"""

from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class Pruebas(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._sin_privacidad = override_settings(PRIVACIDAD_OBLIGATORIA=False)
        self._sin_privacidad.enable()

    def teardown_test_environment(self, **kwargs):
        self._sin_privacidad.disable()
        super().teardown_test_environment(**kwargs)
