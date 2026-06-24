from django.contrib import admin

from .models import Rol


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "descripcion", "activo", "fecha_creacion")
    search_fields = ("nombre", "descripcion")
    list_filter = ("activo",)
    ordering = ("nombre",)