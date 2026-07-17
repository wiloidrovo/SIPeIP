from django.contrib import admin

from .models import EventoAuditoria


@admin.register(EventoAuditoria)
class EventoAuditoriaAdmin(admin.ModelAdmin):
    list_display = (
        "fecha_hora",
        "usuario_identificador",
        "modulo",
        "accion",
        "tipo_entidad",
        "registro_id",
        "resultado",
    )
    list_filter = ("modulo", "accion", "resultado", "fecha_hora")
    search_fields = (
        "usuario_identificador",
        "funcionalidad",
        "tipo_entidad",
        "registro_id",
        "detalle",
    )
    readonly_fields = [field.name for field in EventoAuditoria._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
