from django.apps import AppConfig


class ReportesConfig(AppConfig):
    # Registra el módulo que consulta y exporta información de otras aplicaciones.
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reportes"
    verbose_name = "Reportes"
