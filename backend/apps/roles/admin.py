from django.contrib import admin

from .models import Rol


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    """Configuración del panel administrativo de Django para el modelo Rol."""
    list_display = (
        "id",
        "codigo",
        "nombre",
        "descripcion",
        "alcance",
        "activo",
        "fecha_creacion",
    )
    search_fields = ("codigo", "nombre", "descripcion")
    list_filter = ("activo", "alcance")
    ordering = ("nombre",)
    readonly_fields = ("codigo", "fecha_creacion", "fecha_actualizacion")
