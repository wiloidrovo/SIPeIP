from django.contrib import admin

from .models import (
    HitoProyecto,
    ProyectoInversion,
    SeguimientoProyecto,
    TipologiaIntervencion,
)


@admin.register(TipologiaIntervencion)
class TipologiaIntervencionAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo", "fecha_actualizacion")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre", "descripcion")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")


class HitoProyectoInline(admin.TabularInline):
    model = HitoProyecto
    extra = 0
    fields = (
        "orden",
        "nombre",
        "fecha_inicio_planificada",
        "fecha_fin_planificada",
        "porcentaje_planificado",
        "activo",
    )
    show_change_link = True


@admin.register(ProyectoInversion)
class ProyectoInversionAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "nombre",
        "entidad",
        "estado",
        "responsable",
        "avance_fisico",
        "avance_financiero",
        "activo",
    )
    list_filter = (
        "estado",
        "activo",
        "entidad",
        "tipologia_intervencion__activo",
    )
    search_fields = (
        "codigo",
        "nombre",
        "entidad__codigo_oficial",
        "entidad__nombre",
        "responsable__username",
        "tipologia_intervencion__codigo",
        "tipologia_intervencion__nombre",
    )
    readonly_fields = (
        "estado",
        "activo",
        "avance_fisico",
        "avance_financiero",
        "fecha_creacion",
        "fecha_actualizacion",
    )
    list_select_related = (
        "entidad",
        "plan",
        "objetivo_estrategico",
        "tipologia_intervencion",
        "responsable",
        "creado_por",
    )
    inlines = (HitoProyectoInline,)


@admin.register(HitoProyecto)
class HitoProyectoAdmin(admin.ModelAdmin):
    list_display = (
        "proyecto",
        "orden",
        "nombre",
        "fecha_inicio_planificada",
        "fecha_fin_planificada",
        "porcentaje_planificado",
        "activo",
    )
    list_filter = ("activo", "proyecto__entidad")
    search_fields = ("proyecto__codigo", "proyecto__nombre", "nombre")
    list_select_related = ("proyecto", "proyecto__entidad")


@admin.register(SeguimientoProyecto)
class SeguimientoProyectoAdmin(admin.ModelAdmin):
    list_display = (
        "proyecto",
        "fecha_registro",
        "avance_fisico",
        "avance_financiero",
        "registrado_por",
    )
    list_filter = ("fecha_registro", "proyecto__entidad")
    search_fields = (
        "proyecto__codigo",
        "proyecto__nombre",
        "observacion",
        "registrado_por__username",
    )
    readonly_fields = (
        "proyecto",
        "hito",
        "fecha_registro",
        "avance_fisico",
        "avance_financiero",
        "observacion",
        "registrado_por",
        "fecha_creacion",
    )
    list_select_related = ("proyecto", "proyecto__entidad", "hito", "registrado_por")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
