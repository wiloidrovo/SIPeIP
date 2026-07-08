from django.contrib import admin

from .models import Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """Configuración de administración para planes institucionales."""

    list_display = (
        "nombre",
        "estado",
        "responsable",
        "periodo_inicio",
        "periodo_fin",
        "activo",
    )
    list_filter = ("estado", "activo", "periodo_inicio", "periodo_fin")
    search_fields = ("nombre", "descripcion", "responsable__username")
    ordering = ("-fecha_creacion",)