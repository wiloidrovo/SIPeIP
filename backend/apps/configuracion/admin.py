from django.contrib import admin

from .models import EntidadInstitucional, UnidadOrganizacional


@admin.register(EntidadInstitucional)
class EntidadInstitucionalAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_oficial",
        "nombre",
        "subsector",
        "nivel_gobierno",
        "estado",
        "fecha_actualizacion",
    )
    list_filter = ("estado", "subsector", "nivel_gobierno")
    search_fields = ("codigo_oficial", "nombre", "subsector")
    ordering = ("nombre",)
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")


@admin.register(UnidadOrganizacional)
class UnidadOrganizacionalAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "codigo",
        "entidad",
        "unidad_padre",
        "estado",
        "fecha_actualizacion",
    )
    list_filter = ("estado", "entidad")
    search_fields = (
        "nombre",
        "codigo",
        "entidad__nombre",
        "entidad__codigo_oficial",
    )
    autocomplete_fields = ("entidad", "unidad_padre")
    ordering = ("entidad__nombre", "nombre")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")
