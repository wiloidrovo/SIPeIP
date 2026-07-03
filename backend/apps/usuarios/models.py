from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado que extiende AbstractUser de Django.
    Incorpora la relación con el modelo Rol y estados personalizados para control de acceso.
    """
    class EstadoUsuario(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        INACTIVO = "INACTIVO", "Inactivo"
        BLOQUEADO = "BLOQUEADO", "Bloqueado"

    # Se usa PROTECT para evitar eliminar un rol si todavía tiene usuarios asignados.
    rol = models.ForeignKey(
        "roles.Rol",
        on_delete=models.PROTECT,
        related_name="usuarios",
        null=True,
        blank=True,
    )
    # Define la situación del usuario en el sistema. Debe sincronizarse con is_active de Django.
    estado = models.CharField(
        max_length=20,
        choices=EstadoUsuario.choices,
        default=EstadoUsuario.ACTIVO,
    )
    telefono = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["username"]

    def __str__(self):
        return self.username