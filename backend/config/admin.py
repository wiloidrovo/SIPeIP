"""Sitio administrativo sujeto a la autenticación segura de SIPeIP."""

from django.conf import settings
from django.contrib.admin import AdminSite, ModelAdmin
from django.contrib.admin.apps import AdminConfig
from django.shortcuts import redirect

class SipeipAdminSite(AdminSite):
    site_header = "Administración técnica SIPeIP"
    site_title = "SIPeIP"
    index_title = "Administración técnica"

    def has_permission(self, request):
        # El panel técnico requiere una cuenta activa de superusuario;
        # ser staff o tener un rol administrativo ordinario no es suficiente.
        return (
            super().has_permission(request)
            and request.user.is_superuser
        )

    def register(self, model_or_iterable, admin_class=None, **options):
        """Registra todos los modelos como consulta técnica de solo lectura."""

        # Mantiene filtros y columnas de cada registro, pero bloquea escrituras
        # para que no se omitan las reglas y la auditoría de los servicios de la API.
        base = admin_class or ModelAdmin
        solo_lectura = type(
            f"SoloLectura{base.__name__}",
            (base,),
            {
                "has_add_permission": lambda self, request: False,
                "has_change_permission": (
                    lambda self, request, obj=None: False
                ),
                "has_delete_permission": (
                    lambda self, request, obj=None: False
                ),
            },
        )
        return super().register(model_or_iterable, solo_lectura, **options)

    def login(self, request, extra_context=None):
        """Deshabilita el formulario paralelo y reutiliza la sesión de la API."""

        if self.has_permission(request):
            return redirect("admin:index")
        return redirect(settings.SIPEIP_FRONTEND_LOGIN_URL)


class SipeipAdminConfig(AdminConfig):
    default_site = "config.admin.SipeipAdminSite"
