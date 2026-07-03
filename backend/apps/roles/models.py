from django.db import models


class Rol(models.Model):
    """
    Define los roles del sistema, los cuales agrupan permisos específicos.
    Un rol gestiona el acceso a diferentes módulos y operaciones.
    """
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    
    # Controla si el rol está operativo. Los roles inactivos no otorgan acceso.
    activo = models.BooleanField(default=True)
    
    # Lista flexible de permisos permitidos para este rol.
    # Se usa JSONField para evitar una tabla intermedia y simplificar consultas.
    permisos = models.JSONField(default=list, blank=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre