from django.apps import AppConfig


class ConfiguracionConfig(AppConfig):
    # Registra entidades y unidades; BigAutoField define sus IDs automáticos.
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.configuracion"
    verbose_name = "Configuración institucional"
