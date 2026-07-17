from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


PORCENTAJE_MINIMO = Decimal("0.00")
PORCENTAJE_MAXIMO = Decimal("100.00")
VALIDADORES_PORCENTAJE = [
    MinValueValidator(
        PORCENTAJE_MINIMO,
        "El porcentaje no puede ser negativo.",
    ),
    MaxValueValidator(
        PORCENTAJE_MAXIMO,
        "El porcentaje no puede superar el 100%.",
    ),
]


class TipologiaIntervencion(models.Model):
    """Catálogo configurable de tipologías para proyectos de inversión."""

    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tipología de intervención"
        verbose_name_plural = "Tipologías de intervención"
        ordering = ["nombre", "codigo"]
        constraints = [
            models.UniqueConstraint(
                Lower("codigo"),
                name="uniq_tipologia_intervencion_codigo_ci",
            ),
            models.UniqueConstraint(
                Lower("nombre"),
                name="uniq_tipologia_intervencion_nombre_ci",
            ),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def clean(self):
        super().clean()
        self.codigo = (self.codigo or "").strip().upper()
        self.nombre = (self.nombre or "").strip()
        self.descripcion = (self.descripcion or "").strip()
        errores = {}
        if not self.codigo:
            errores["codigo"] = "El código de la tipología es obligatorio."
        if not self.nombre:
            errores["nombre"] = "El nombre de la tipología es obligatorio."
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.codigo = (self.codigo or "").strip().upper()
        self.nombre = (self.nombre or "").strip()
        self.descripcion = (self.descripcion or "").strip()
        return super().save(*args, **kwargs)


class ProyectoInversion(models.Model):
    """Proyecto de inversión vinculado con la planificación institucional."""

    class EstadoProyecto(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        PLANIFICADO = "PLANIFICADO", "Planificado"
        EN_REVISION = "EN_REVISION", "En revisión"
        APROBADO = "APROBADO", "Aprobado"
        EN_EJECUCION = "EN_EJECUCION", "En ejecución"
        SUSPENDIDO = "SUSPENDIDO", "Suspendido"
        FINALIZADO = "FINALIZADO", "Finalizado"
        ARCHIVADO = "ARCHIVADO", "Archivado"

    entidad = models.ForeignKey(
        "configuracion.EntidadInstitucional",
        on_delete=models.PROTECT,
        related_name="proyectos_inversion",
    )
    plan = models.ForeignKey(
        "planes.Plan",
        on_delete=models.PROTECT,
        related_name="proyectos_inversion",
    )
    objetivo_estrategico = models.ForeignKey(
        "objetivos.ObjetivoEstrategico",
        on_delete=models.PROTECT,
        related_name="proyectos_inversion",
    )
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    tipologia_intervencion = models.ForeignKey(
        TipologiaIntervencion,
        on_delete=models.PROTECT,
        related_name="proyectos",
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="proyectos_inversion_responsables",
        null=True,
        blank=True,
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="proyectos_inversion_creados",
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    presupuesto_estimado = models.DecimalField(max_digits=16, decimal_places=2)
    avance_fisico = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=PORCENTAJE_MINIMO,
        validators=VALIDADORES_PORCENTAJE,
    )
    avance_financiero = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=PORCENTAJE_MINIMO,
        validators=VALIDADORES_PORCENTAJE,
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoProyecto.choices,
        default=EstadoProyecto.BORRADOR,
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proyecto de inversión"
        verbose_name_plural = "Proyectos de inversión"
        ordering = ["-fecha_creacion", "codigo"]
        constraints = [
            models.UniqueConstraint(
                Lower("codigo"),
                "entidad",
                name="uniq_proyecto_entidad_codigo_ci",
            ),
            models.CheckConstraint(
                condition=models.Q(presupuesto_estimado__gte=0),
                name="ck_proyecto_presupuesto_no_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(fecha_fin__gte=models.F("fecha_inicio")),
                name="ck_proyecto_rango_fechas_valido",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    avance_fisico__gte=0,
                    avance_fisico__lte=100,
                ),
                name="ck_proyecto_avance_fisico",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    avance_financiero__gte=0,
                    avance_financiero__lte=100,
                ),
                name="ck_proyecto_avance_financiero",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    estado__in=[
                        "BORRADOR",
                        "PLANIFICADO",
                        "EN_REVISION",
                        "APROBADO",
                        "EN_EJECUCION",
                        "SUSPENDIDO",
                        "FINALIZADO",
                        "ARCHIVADO",
                    ]
                ),
                name="ck_proyecto_estado",
            ),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def clean(self):
        super().clean()
        self.codigo = (self.codigo or "").strip().upper()
        self.nombre = (self.nombre or "").strip()
        self.descripcion = (self.descripcion or "").strip()
        errores = {}

        if not self.codigo:
            errores["codigo"] = "El código del proyecto es obligatorio."
        if not self.nombre:
            errores["nombre"] = "El nombre del proyecto es obligatorio."
        if not self.tipologia_intervencion_id:
            errores["tipologia_intervencion"] = (
                "La tipología de intervención es obligatoria."
            )
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            errores["fecha_fin"] = (
                "La fecha de finalización no puede ser anterior a la fecha de inicio."
            )
        if self.presupuesto_estimado is not None and self.presupuesto_estimado < 0:
            errores["presupuesto_estimado"] = (
                "El presupuesto estimado no puede ser negativo."
            )

        if (
            self.entidad_id
            and self.objetivo_estrategico_id
            and self.objetivo_estrategico.entidad_id != self.entidad_id
        ):
            errores["objetivo_estrategico"] = (
                "El objetivo estratégico debe pertenecer a la entidad del proyecto."
            )

        entidad_plan_id = getattr(self.plan, "entidad_id", None) if self.plan_id else None
        if entidad_plan_id != self.entidad_id:
            errores["plan"] = "El plan debe pertenecer a la entidad del proyecto."

        entidad_responsable_id = (
            getattr(self.responsable, "entidad_id", None)
            if self.responsable_id
            else None
        )
        if self.responsable_id and entidad_responsable_id != self.entidad_id:
            errores["responsable"] = (
                "El responsable debe pertenecer a la entidad del proyecto."
            )

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.codigo = (self.codigo or "").strip().upper()
        self.nombre = (self.nombre or "").strip()
        self.descripcion = (self.descripcion or "").strip()
        return super().save(*args, **kwargs)


class HitoProyecto(models.Model):
    """Hito ordenado que conforma el cronograma básico de un proyecto."""

    proyecto = models.ForeignKey(
        ProyectoInversion,
        on_delete=models.PROTECT,
        related_name="hitos",
    )
    orden = models.PositiveIntegerField()
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    fecha_inicio_planificada = models.DateField()
    fecha_fin_planificada = models.DateField()
    porcentaje_planificado = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=VALIDADORES_PORCENTAJE,
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Hito de proyecto"
        verbose_name_plural = "Hitos de proyecto"
        ordering = ["proyecto", "orden"]
        constraints = [
            models.UniqueConstraint(
                fields=["proyecto", "orden"],
                name="uniq_hito_proyecto_orden",
            ),
            models.UniqueConstraint(
                Lower("nombre"),
                "proyecto",
                name="uniq_hito_proyecto_nombre_ci",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    fecha_fin_planificada__gte=models.F("fecha_inicio_planificada")
                ),
                name="ck_hito_rango_fechas_valido",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    porcentaje_planificado__gte=0,
                    porcentaje_planificado__lte=100,
                ),
                name="ck_hito_porcentaje_planificado",
            ),
        ]

    def __str__(self):
        return f"{self.proyecto.codigo} - {self.orden}. {self.nombre}"

    def clean(self):
        super().clean()
        self.nombre = (self.nombre or "").strip()
        self.descripcion = (self.descripcion or "").strip()
        errores = {}

        if not self.nombre:
            errores["nombre"] = "El nombre del hito es obligatorio."
        if (
            self.fecha_inicio_planificada
            and self.fecha_fin_planificada
            and self.fecha_fin_planificada < self.fecha_inicio_planificada
        ):
            errores["fecha_fin_planificada"] = (
                "La fecha final del hito no puede ser anterior a la fecha inicial."
            )

        if self.proyecto_id:
            if (
                self.fecha_inicio_planificada
                and self.fecha_inicio_planificada < self.proyecto.fecha_inicio
            ):
                errores["fecha_inicio_planificada"] = (
                    "El hito no puede iniciar antes que el proyecto."
                )
            if (
                self.fecha_fin_planificada
                and self.fecha_fin_planificada > self.proyecto.fecha_fin
            ):
                errores["fecha_fin_planificada"] = (
                    "El hito no puede finalizar después que el proyecto."
                )

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.nombre = (self.nombre or "").strip()
        self.descripcion = (self.descripcion or "").strip()
        return super().save(*args, **kwargs)


class SeguimientoProyecto(models.Model):
    """Corte histórico e inmutable de avance físico y financiero."""

    proyecto = models.ForeignKey(
        ProyectoInversion,
        on_delete=models.PROTECT,
        related_name="seguimientos",
    )
    hito = models.ForeignKey(
        HitoProyecto,
        on_delete=models.PROTECT,
        related_name="seguimientos",
        null=True,
        blank=True,
    )
    fecha_registro = models.DateField(default=timezone.localdate)
    avance_fisico = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=VALIDADORES_PORCENTAJE,
    )
    avance_financiero = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=VALIDADORES_PORCENTAJE,
    )
    observacion = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="seguimientos_proyectos",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Seguimiento de proyecto"
        verbose_name_plural = "Seguimientos de proyectos"
        ordering = ["-fecha_registro", "-fecha_creacion"]
        constraints = [
            models.UniqueConstraint(
                fields=["proyecto", "fecha_registro"],
                name="uniq_seguimiento_proyecto_fecha",
            ),
            models.CheckConstraint(
                condition=models.Q(avance_fisico__gte=0, avance_fisico__lte=100),
                name="ck_seguimiento_avance_fisico",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    avance_financiero__gte=0,
                    avance_financiero__lte=100,
                ),
                name="ck_seguimiento_avance_financiero",
            ),
        ]

    def __str__(self):
        return f"{self.proyecto.codigo} - {self.fecha_registro}"

    def clean(self):
        super().clean()
        self.observacion = (self.observacion or "").strip()
        errores = {}

        if self.hito_id and self.hito.proyecto_id != self.proyecto_id:
            errores["hito"] = "El hito debe pertenecer al proyecto del seguimiento."

        if self.proyecto_id and self.fecha_registro:
            if not self.proyecto.fecha_inicio <= self.fecha_registro <= self.proyecto.fecha_fin:
                errores["fecha_registro"] = (
                    "La fecha del seguimiento debe estar dentro del periodo del proyecto."
                )

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.observacion = (self.observacion or "").strip()
        return super().save(*args, **kwargs)
