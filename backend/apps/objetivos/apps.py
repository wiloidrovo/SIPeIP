from django.apps import AppConfig


class ObjetivosConfig(AppConfig):
    # Registra objetivos institucionales, catálogos PND/ODS y sus alineaciones.
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.objetivos"
    verbose_name = "Objetivos y alineación"
