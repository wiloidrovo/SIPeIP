from django.contrib import admin

from .models import HistorialEstadoPlan, Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """Configuración de administración para planes institucionales."""

    list_display = (
        "nombre",
        "estado",
        "entidad",
        "responsable",
        "creado_por",
        "periodo_inicio",
        "periodo_fin",
        "activo",
    )
    list_filter = ("estado", "activo", "entidad", "periodo_inicio", "periodo_fin")
    search_fields = ("nombre", "descripcion", "responsable__username")
    ordering = ("-fecha_creacion",)


@admin.register(HistorialEstadoPlan)
class HistorialEstadoPlanAdmin(admin.ModelAdmin):
    list_display = (
        "plan",
        "accion",
        "estado_anterior",
        "estado_nuevo",
        "usuario",
        "fecha",
    )
    list_filter = ("accion", "estado_nuevo", "fecha")
    search_fields = ("plan__nombre", "usuario__username", "observacion")
    readonly_fields = (
        "plan",
        "usuario",
        "accion",
        "estado_anterior",
        "estado_nuevo",
        "observacion",
        "fecha",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
