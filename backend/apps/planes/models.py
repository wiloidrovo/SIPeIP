from django.conf import settings
from django.core.exceptions import ValidationError
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
    revisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="planes_revisados",
        null=True,
        blank=True,
        editable=False,
    )
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="planes_aprobados",
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
    fecha_envio_revision = models.DateTimeField(null=True, blank=True, editable=False)
    fecha_inicio_revision = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    fecha_aprobacion = models.DateTimeField(null=True, blank=True, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    objetivos_estrategicos = models.ManyToManyField(
        "objetivos.ObjetivoEstrategico",
        through="metas.Meta",
        related_name="planes",
        blank=True,
    )

    class Meta:
        verbose_name = "Plan"
        verbose_name_plural = "Planes"
        ordering = ["-fecha_creacion"]
        constraints = [
            models.UniqueConstraint(
                fields=["entidad", "nombre"],
                name="unique_plan_nombre_por_entidad",
            ),
            models.CheckConstraint(
                condition=models.Q(periodo_fin__gte=models.F("periodo_inicio")),
                name="plan_rango_fechas_valido",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        revisor__isnull=True,
                        fecha_inicio_revision__isnull=True,
                    )
                    | models.Q(
                        revisor__isnull=False,
                        fecha_inicio_revision__isnull=False,
                    )
                ),
                name="plan_revisor_fecha_coherentes",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        aprobado_por__isnull=True,
                        fecha_aprobacion__isnull=True,
                    )
                    | models.Q(
                        aprobado_por__isnull=False,
                        fecha_aprobacion__isnull=False,
                    )
                ),
                name="plan_aprobador_fecha_coherentes",
            ),
        ]

    def __str__(self):
        return self.nombre

    def clean(self):
        """Valida invariantes del periodo y de la trazabilidad de revisión."""

        super().clean()
        errores = {}

        if (
            self.periodo_inicio
            and self.periodo_fin
            and self.periodo_fin < self.periodo_inicio
        ):
            errores["periodo_fin"] = (
                "La fecha de finalización no puede ser anterior a la fecha de inicio."
            )

        if bool(self.revisor_id) != bool(self.fecha_inicio_revision):
            errores["revisor"] = (
                "El revisor y la fecha de inicio de revisión deben registrarse juntos."
            )

        if bool(self.aprobado_por_id) != bool(self.fecha_aprobacion):
            errores["aprobado_por"] = (
                "El aprobador y la fecha de aprobación deben registrarse juntos."
            )

        if (
            self.fecha_envio_revision
            and self.fecha_inicio_revision
            and self.fecha_inicio_revision < self.fecha_envio_revision
        ):
            errores["fecha_inicio_revision"] = (
                "La revisión no puede iniciar antes del envío del plan."
            )

        if (
            self.fecha_inicio_revision
            and self.fecha_aprobacion
            and self.fecha_aprobacion < self.fecha_inicio_revision
        ):
            errores["fecha_aprobacion"] = (
                "La aprobación no puede ser anterior al inicio de la revisión."
            )

        if errores:
            raise ValidationError(errores)


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
