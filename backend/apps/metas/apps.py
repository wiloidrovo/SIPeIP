from django.apps import AppConfig


class MetasConfig(AppConfig):
    """Configuración de la aplicación de metas, indicadores y avances."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.metas"
    verbose_name = "Gestión de metas e indicadores"