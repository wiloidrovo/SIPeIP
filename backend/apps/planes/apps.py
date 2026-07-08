from django.apps import AppConfig


class PlanesConfig(AppConfig):
    """Configuración de la aplicación de gestión de planes institucionales."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.planes"
    verbose_name = "Gestión de planes"