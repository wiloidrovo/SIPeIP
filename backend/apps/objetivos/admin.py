from django.contrib import admin

from .models import Alineacion, EjePND, ObjetivoEstrategico, ObjetivoPND, ODS


@admin.register(ObjetivoEstrategico)
class ObjetivoEstrategicoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "nombre",
        "entidad",
        "estado",
        "fecha_actualizacion",
    )
    list_filter = ("estado", "entidad")
    search_fields = ("codigo", "nombre", "descripcion", "entidad__nombre")
    autocomplete_fields = ("entidad",)
    ordering = ("entidad__nombre", "codigo")


@admin.register(EjePND)
class EjePNDAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "estado", "fecha_actualizacion")
    list_filter = ("estado",)
    search_fields = ("codigo", "nombre", "descripcion")
    ordering = ("codigo",)


@admin.register(ObjetivoPND)
class ObjetivoPNDAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "eje", "estado", "fecha_actualizacion")
    list_filter = ("estado", "eje")
    search_fields = ("codigo", "nombre", "descripcion", "eje__nombre")
    autocomplete_fields = ("eje",)
    ordering = ("eje__codigo", "codigo")


@admin.register(ODS)
class ODSAdmin(admin.ModelAdmin):
    list_display = ("numero", "nombre", "estado", "fecha_actualizacion")
    list_filter = ("estado",)
    search_fields = ("numero", "nombre", "descripcion")
    ordering = ("numero",)


@admin.register(Alineacion)
class AlineacionAdmin(admin.ModelAdmin):
    list_display = (
        "objetivo_estrategico",
        "objetivo_pnd",
        "ods",
        "estado",
        "usuario_creador",
        "usuario_validador",
        "fecha_actualizacion",
    )
    list_filter = ("estado", "objetivo_estrategico__entidad", "ods")
    search_fields = (
        "objetivo_estrategico__codigo",
        "objetivo_estrategico__nombre",
        "objetivo_pnd__codigo",
        "objetivo_pnd__nombre",
        "ods__nombre",
        "justificacion",
        "usuario_creador__username",
        "usuario_validador__username",
    )
    autocomplete_fields = (
        "objetivo_estrategico",
        "objetivo_pnd",
        "ods",
        "usuario_creador",
        "usuario_validador",
    )
    readonly_fields = (
        "estado",
        "usuario_creador",
        "usuario_validador",
        "fecha_creacion",
        "fecha_actualizacion",
    )
    ordering = ("-fecha_actualizacion",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
