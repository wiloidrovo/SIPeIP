from django.core.exceptions import ValidationError
from django.db import models


class Rol(models.Model):
    """
    Define los roles del sistema, los cuales agrupan permisos específicos.
    Un rol gestiona el acceso a diferentes módulos y operaciones.
    """

    class Alcance(models.TextChoices):
        TOTAL = "TOTAL", "Total"
        GLOBAL = "GLOBAL", "Global administrativo"
        ENTIDAD = "ENTIDAD", "Institución asignada"
        PROPIO_ASIGNADO = "PROPIO_ASIGNADO", "Propios y asignados"
        REVISION_ENTIDAD = "REVISION_ENTIDAD", "Revisión institucional"
        LECTURA_ENTIDAD = "LECTURA_ENTIDAD", "Lectura institucional"

    nombre = models.CharField(max_length=100, unique=True)
    # Identificador estable para roles institucionales. Los roles personalizados
    # conservan NULL y la autorización nunca depende de este código o del nombre.
    codigo = models.SlugField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )
    descripcion = models.TextField(blank=True)
    
    # Controla si el rol está operativo. Los roles inactivos no otorgan acceso.
    activo = models.BooleanField(default=True)
    
    # Lista flexible de permisos permitidos para este rol.
    # Se usa JSONField para evitar una tabla intermedia y simplificar consultas.
    permisos = models.JSONField(default=list, blank=True)
    alcance = models.CharField(
        max_length=30,
        choices=Alcance.choices,
        default=Alcance.ENTIDAD,
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def clean(self):
        """Impide guardar permisos fuera del catálogo desde formularios/Admin."""

        super().clean()
        from .permissions import ALLOWED_ROLE_PERMISSIONS

        if not isinstance(self.permisos, list):
            raise ValidationError({"permisos": "Los permisos deben ser una lista."})

        invalidos = [
            permiso
            for permiso in self.permisos
            if not isinstance(permiso, str)
            or permiso not in ALLOWED_ROLE_PERMISSIONS
        ]
        if invalidos:
            raise ValidationError(
                {"permisos": "La lista contiene permisos no reconocidos."}
            )
