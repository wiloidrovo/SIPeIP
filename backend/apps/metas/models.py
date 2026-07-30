from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Meta(models.Model):
    """
    Representa una meta institucional asociada a un plan.

    La meta define un resultado esperado dentro de un periodo determinado.
    Cada meta puede tener varios indicadores para medir su cumplimiento.
    """

    class EstadoMeta(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        ACTIVA = "ACTIVA", "Activa"
        CERRADA = "CERRADA", "Cerrada"
        ARCHIVADA = "ARCHIVADA", "Archivada"

    plan = models.ForeignKey(
        "planes.Plan",
        on_delete=models.PROTECT,
        related_name="metas",
    )
    objetivo_estrategico = models.ForeignKey(
        "objetivos.ObjetivoEstrategico",
        on_delete=models.PROTECT,
        related_name="metas",
    )
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    resultado_esperado = models.TextField(blank=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(
        max_length=20,
        choices=EstadoMeta.choices,
        default=EstadoMeta.BORRADOR,
    )
    activa = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Meta"
        verbose_name_plural = "Metas"
        ordering = ["-fecha_creacion"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "nombre"],
                name="unique_meta_por_plan",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(estado="ACTIVA", activa=True)
                    | models.Q(
                        estado__in=["BORRADOR", "CERRADA", "ARCHIVADA"],
                        activa=False,
                    )
                ),
                name="meta_estado_activa_coherente",
            ),
        ]

    def __str__(self):
        return self.nombre

    def clean(self):
        """Mantiene coherente la meta con su plan y objetivo institucional."""

        super().clean()
        errores = {}

        if self.plan_id and self.objetivo_estrategico_id:
            if self.plan.entidad_id != self.objetivo_estrategico.entidad_id:
                errores["objetivo_estrategico"] = (
                    "El objetivo estratégico debe pertenecer a la entidad del plan."
                )
            objetivo_existente_id = None
            if self.pk:
                objetivo_existente_id = (
                    type(self).objects.filter(pk=self.pk).values_list(
                        "objetivo_estrategico_id",
                        flat=True,
                    ).first()
                )
            conserva_objetivo_existente = (
                objetivo_existente_id == self.objetivo_estrategico_id
            )
            if (
                self.objetivo_estrategico.estado != "ACTIVO"
                and not conserva_objetivo_existente
            ):
                errores["objetivo_estrategico"] = (
                    "Solo puede utilizar un objetivo estratégico activo."
                )

        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_fin < self.fecha_inicio:
                errores["fecha_fin"] = (
                    "La fecha de finalización no puede ser anterior a la fecha de inicio."
                )
            if self.plan_id:
                if self.fecha_inicio < self.plan.periodo_inicio:
                    errores["fecha_inicio"] = (
                        "La meta no puede iniciar antes del periodo del plan."
                    )
                if self.fecha_fin > self.plan.periodo_fin:
                    errores["fecha_fin"] = (
                        "La meta no puede finalizar después del periodo del plan."
                    )

        if errores:
            raise ValidationError(errores)


class Indicador(models.Model):
    """
    Indicador usado para medir el cumplimiento de una meta institucional.

    El valor actual se actualiza a partir de los avances registrados. Esto
    permite consultar rápidamente el estado más reciente del indicador.
    """

    class FrecuenciaMedicion(models.TextChoices):
        MENSUAL = "MENSUAL", "Mensual"
        TRIMESTRAL = "TRIMESTRAL", "Trimestral"
        SEMESTRAL = "SEMESTRAL", "Semestral"
        ANUAL = "ANUAL", "Anual"

    class SentidoMedicion(models.TextChoices):
        ASCENDENTE = "ASCENDENTE", "Ascendente"
        DESCENDENTE = "DESCENDENTE", "Descendente"

    meta = models.ForeignKey(
        Meta,
        on_delete=models.PROTECT,
        related_name="indicadores",
    )
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    unidad_medida = models.CharField(max_length=50)
    valor_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_meta = models.DecimalField(max_digits=12, decimal_places=2)
    valor_actual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    frecuencia = models.CharField(
        max_length=20,
        choices=FrecuenciaMedicion.choices,
        default=FrecuenciaMedicion.TRIMESTRAL,
    )
    sentido = models.CharField(
        max_length=20,
        choices=SentidoMedicion.choices,
        default=SentidoMedicion.ASCENDENTE,
    )
    ponderacion = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("100.00"),
        validators=[
            MinValueValidator(
                Decimal("0.01"),
                "La ponderación debe ser mayor que cero.",
            ),
            MaxValueValidator(
                Decimal("100.00"),
                "La ponderación no puede superar 100.",
            ),
        ],
    )
    activo = models.BooleanField(default=True)
    validado = models.BooleanField(default=False)
    validado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="indicadores_validados",
        null=True,
        blank=True,
    )
    fecha_validacion = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Indicador"
        verbose_name_plural = "Indicadores"
        ordering = ["-fecha_creacion"]
        constraints = [
            models.UniqueConstraint(
                fields=["meta", "nombre"],
                name="unique_indicador_por_meta",
            ),
            models.CheckConstraint(
                condition=models.Q(valor_base__gte=0),
                name="indicador_valor_base_no_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(valor_meta__gte=0),
                name="indicador_valor_meta_no_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(valor_actual__gte=0),
                name="indicador_valor_actual_no_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    ponderacion__gt=0,
                    ponderacion__lte=100,
                ),
                name="indicador_ponderacion_valida",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        sentido="ASCENDENTE",
                        valor_meta__gte=models.F("valor_base"),
                    )
                    | models.Q(
                        sentido="DESCENDENTE",
                        valor_meta__lt=models.F("valor_base"),
                    )
                ),
                name="indicador_sentido_valores_coherentes",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        validado=False,
                        validado_por__isnull=True,
                        fecha_validacion__isnull=True,
                    )
                    | models.Q(
                        validado=True,
                        validado_por__isnull=False,
                        fecha_validacion__isnull=False,
                    )
                ),
                name="indicador_validacion_coherente",
            ),
        ]

    def __str__(self):
        return self.nombre

    def clean(self):
        """Valida valores, sentido y trazabilidad de la validación."""

        super().clean()
        errores = {}

        if self.valor_base is not None and self.valor_base < 0:
            errores["valor_base"] = "El valor base no puede ser negativo."
        if self.valor_meta is not None and self.valor_meta < 0:
            errores["valor_meta"] = "El valor meta no puede ser negativo."
        if self.valor_actual is not None and self.valor_actual < 0:
            errores["valor_actual"] = "El valor actual no puede ser negativo."
        if self.ponderacion is not None and not (
            Decimal("0.01") <= self.ponderacion <= Decimal("100.00")
        ):
            errores["ponderacion"] = (
                "La ponderación debe estar entre 0.01 y 100."
            )

        if (
            self.sentido == self.SentidoMedicion.ASCENDENTE
            and self.valor_base is not None
            and self.valor_meta is not None
            and self.valor_meta <= self.valor_base
        ):
            errores["valor_meta"] = (
                "En un indicador ascendente, el valor meta debe ser "
                "mayor que el valor base."
            )
        if (
            self.sentido == self.SentidoMedicion.DESCENDENTE
            and self.valor_base is not None
            and self.valor_meta is not None
            and self.valor_meta >= self.valor_base
        ):
            errores["valor_meta"] = (
                "En un indicador descendente, el valor meta debe ser "
                "menor que el valor base."
            )

        validacion_completa = bool(self.validado_por_id) and bool(
            self.fecha_validacion
        )
        if self.validado != validacion_completa:
            errores["validado"] = (
                "El estado validado, el usuario validador y la fecha de "
                "validación deben ser coherentes."
            )

        if errores:
            raise ValidationError(errores)


class AvanceIndicador(models.Model):
    """
    Registro histórico de avance de un indicador.

    Cada avance conserva el valor reportado en una fecha específica. Al crear
    un avance desde la API, el indicador asociado actualiza su valor actual.
    """

    indicador = models.ForeignKey(
        Indicador,
        on_delete=models.PROTECT,
        related_name="avances",
    )
    fecha_registro = models.DateField()
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    observacion = models.TextField(blank=True)
    evidencia = models.CharField(max_length=500, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="avances_indicadores",
        null=True,
        blank=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Avance de indicador"
        verbose_name_plural = "Avances de indicadores"
        ordering = ["-fecha_registro", "-fecha_creacion"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor__gte=0),
                name="avance_indicador_valor_no_negativo",
            ),
        ]

    def __str__(self):
        return f"{self.indicador.nombre} - {self.fecha_registro}"

    def clean(self):
        """Valida que la medición pertenezca al periodo de su meta."""

        super().clean()
        errores = {}

        if self.valor is not None and self.valor < 0:
            errores["valor"] = "El valor del avance no puede ser negativo."

        if self.fecha_registro:
            if self.fecha_registro > timezone.localdate():
                errores["fecha_registro"] = (
                    "La fecha del avance no puede estar en el futuro."
                )
            if self.indicador_id:
                meta = self.indicador.meta
                if not meta.fecha_inicio <= self.fecha_registro <= meta.fecha_fin:
                    errores["fecha_registro"] = (
                        "La fecha del avance debe estar dentro del periodo de la meta."
                    )

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.observacion = (self.observacion or "").strip()
        self.evidencia = (self.evidencia or "").strip()
        return super().save(*args, **kwargs)
