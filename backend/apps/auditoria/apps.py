from django.apps import AppConfig


class AuditoriaConfig(AppConfig):
    # Registra la bitácora en Django y asigna el nombre visible del módulo.
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auditoria"
    verbose_name = "Auditoría y trazabilidad"
