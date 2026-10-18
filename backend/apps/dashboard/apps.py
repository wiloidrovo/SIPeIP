from django.apps import AppConfig


class DashboardConfig(AppConfig):
    # Registra el módulo del panel; los resúmenes se calculan en sus vistas.
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboard"
    verbose_name = "Panel institucional"
