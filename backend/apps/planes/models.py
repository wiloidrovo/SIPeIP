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
        EN_REVISION_INICIADA = "EN_REVISION_INICIADA", "Revisión iniciada"
        APROBADO = "APROBADO", "Aprobado"
        DEVUELTO = "DEVUELTO", "Devuelto"
        RECHAZADO = "RECHAZADO", "Rechazado"
        ARCHIVADO = "ARCHIVADO", "Archivado"

    nombre = models.CharField(max_length=150)
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
    entidad = models.ForeignKey(
        "configuracion.EntidadInstitucional",
        on_delete=models.PROTECT,
        related_name="planes",
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="planes_creados",
        null=True,
        blank=True,
        editable=False,
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
        constraints = [
            models.UniqueConstraint(
                fields=["entidad", "nombre"],
                name="unique_plan_nombre_por_entidad",
            )
        ]

    def __str__(self):
        return self.nombre


class HistorialEstadoPlan(models.Model):
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="historial_estados",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transiciones_planes",
    )
    accion = models.CharField(max_length=40)
    estado_anterior = models.CharField(max_length=30)
    estado_nuevo = models.CharField(max_length=30)
    observacion = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historial de estado de plan"
        verbose_name_plural = "Historiales de estado de planes"
        ordering = ["-fecha", "-id"]
        indexes = [models.Index(fields=["plan", "fecha"])]

    def __str__(self):
        return f"{self.plan} - {self.accion}"
