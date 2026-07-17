from django.apps import AppConfig


class AutenticacionConfig(AppConfig):
    """Configuración del módulo de autenticación."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.autenticacion"
    verbose_name = "Autenticación"
