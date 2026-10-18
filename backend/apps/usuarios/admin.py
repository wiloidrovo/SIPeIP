from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


# Amplía la ficha estándar de Django con adscripción y rol institucional.
# El sitio técnico restringe el acceso y mantiene la consulta de solo lectura.
@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Configuración del panel administrativo de Django para el modelo Usuario."""
    list_display = (
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
        "rol",
        "entidad",
        "unidad_organizacional",
        "estado",
        "is_active",
        "is_staff",
    )

    list_filter = (
        "estado",
        "rol",
        "entidad",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
    )

    ordering = ("username",)

    fieldsets = UserAdmin.fieldsets + (
        (
            "Información SIPeIP",
            {
                "fields": (
                    "rol",
                    "estado",
                    "telefono",
                    "entidad",
                    "unidad_organizacional",
                )
            },
        ),
    )
