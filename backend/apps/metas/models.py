from django.conf import settings
from django.db import models


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
    activa = models.BooleanField(default=True)
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
            )
        ]

    def __str__(self):
        return self.nombre


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
    activo = models.BooleanField(default=True)
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
            )
        ]

    def __str__(self):
        return self.nombre


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

    def __str__(self):
        return f"{self.indicador.nombre} - {self.fecha_registro}"