from django.conf import settings
from django.db import models


class Plan(models.Model):
    """
    Representa un plan institucional dentro del sistema SIPeIP.

    El modelo permite registrar planes en estado inicial de borrador y avanzar
    su flujo hacia revisión. La relación con el usuario responsable permite
    mantener trazabilidad sobre quién administra o coordina el plan.
    """

    class EstadoPlan(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        EN_REVISION = "EN_REVISION", "En revisión"
        APROBADO = "APROBADO", "Aprobado"
        RECHAZADO = "RECHAZADO", "Rechazado"
        ARCHIVADO = "ARCHIVADO", "Archivado"

    nombre = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(blank=True)
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="planes_responsables",
        null=True,
        blank=True,
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoPlan.choices,
        default=EstadoPlan.BORRADOR,
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Plan"
        verbose_name_plural = "Planes"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre