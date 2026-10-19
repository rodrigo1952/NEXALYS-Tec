from django.apps import AppConfig


class FavoritosConfig(AppConfig):
    name = "favoritos"
    verbose_name = "Favoritos"

    def ready(self):
        # Conecta la señal que guarda el favorito pendiente al iniciar sesión.
        from . import signals  # noqa: F401
