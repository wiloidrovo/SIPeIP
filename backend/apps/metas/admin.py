from django.contrib import admin

from .models import AvanceIndicador, Indicador, Meta


@admin.register(Meta)
class MetaAdmin(admin.ModelAdmin):
    """Configuración administrativa para metas institucionales."""

    list_display = ("nombre", "plan", "estado", "fecha_inicio", "fecha_fin", "activa")
    list_filter = ("estado", "activa", "fecha_inicio", "fecha_fin")
    search_fields = ("nombre", "descripcion", "plan__nombre")
    ordering = ("-fecha_creacion",)


@admin.register(Indicador)
class IndicadorAdmin(admin.ModelAdmin):
    """Configuración administrativa para indicadores."""

    list_display = (
        "nombre",
        "meta",
        "unidad_medida",
        "valor_actual",
        "valor_meta",
        "frecuencia",
        "activo",
    )
    list_filter = ("frecuencia", "activo")
    search_fields = ("nombre", "descripcion", "meta__nombre")
    ordering = ("-fecha_creacion",)


@admin.register(AvanceIndicador)
class AvanceIndicadorAdmin(admin.ModelAdmin):
    """Configuración administrativa para avances de indicadores."""

    list_display = ("indicador", "fecha_registro", "valor", "registrado_por")
    list_filter = ("fecha_registro",)
    search_fields = ("indicador__nombre", "observacion")
    ordering = ("-fecha_registro", "-fecha_creacion")