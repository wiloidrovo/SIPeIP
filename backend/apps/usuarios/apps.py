from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    """Configuración de la aplicación de usuarios."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.usuarios"
    verbose_name = "Usuarios"