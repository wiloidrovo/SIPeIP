from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower


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
    entidad = models.ForeignKey(
        "configuracion.EntidadInstitucional",
        on_delete=models.PROTECT,
        related_name="usuarios",
        null=True,
        blank=True,
    )
    unidad_organizacional = models.ForeignKey(
        "configuracion.UnidadOrganizacional",
        on_delete=models.PROTECT,
        related_name="usuarios",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["username"]
        constraints = [
            models.UniqueConstraint(
                Lower("username"),
                name="usuario_username_unico_sin_mayusculas",
            ),
            models.UniqueConstraint(
                Lower("email"),
                condition=~models.Q(email=""),
                name="usuario_email_unico_sin_mayusculas",
            ),
        ]

    def get_sipeip_permissions(self):
        """Devuelve los permisos efectivos del catálogo SIPeIP para el usuario."""

        from apps.roles.permissions import ALLOWED_ROLE_PERMISSIONS

        permisos_catalogo = set(ALLOWED_ROLE_PERMISSIONS)

        if not self.is_active or self.estado != self.EstadoUsuario.ACTIVO:
            return set()

        if self.is_superuser:
            return permisos_catalogo

        if not self.rol_id or not self.rol.activo:
            return set()

        from apps.configuracion.scope import ALCANCES_INSTITUCIONALES

        if self.rol.alcance in ALCANCES_INSTITUCIONALES:
            entidad = getattr(self, "entidad", None)
            if entidad is None or getattr(entidad, "estado", None) != "ACTIVA":
                return set()

        permisos_rol = self.rol.permisos

        if not isinstance(permisos_rol, list):
            return set()

        return permisos_catalogo.intersection(permisos_rol)

    def clean(self):
        super().clean()
        self._validar_adscripcion()

    def _validar_adscripcion(self):
        if self.unidad_organizacional_id and (
            self.entidad_id is None
            or self.unidad_organizacional.entidad_id != self.entidad_id
        ):
            raise ValidationError(
                {
                    "unidad_organizacional": (
                        "La unidad organizacional debe pertenecer a la entidad asignada."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self._validar_adscripcion()
        return super().save(*args, **kwargs)

    def tiene_permiso(self, codigo_permiso):
        """Comprueba un permiso SIPeIP sin depender del nombre del rol."""

        return codigo_permiso in self.get_sipeip_permissions()

    def __str__(self):
        return self.username
