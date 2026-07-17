from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower


class EstadoCatalogo(models.TextChoices):
    ACTIVO = "ACTIVO", "Activo"
    INACTIVO = "INACTIVO", "Inactivo"


def _normalizar_textos(instancia, *, incluye_codigo=True):
    if incluye_codigo:
        instancia.codigo = (instancia.codigo or "").strip().upper()
    instancia.nombre = (instancia.nombre or "").strip()
    instancia.descripcion = (instancia.descripcion or "").strip()


class ObjetivoEstrategico(models.Model):
    """Objetivo estratégico definido dentro de una entidad institucional."""

    entidad = models.ForeignKey(
        "configuracion.EntidadInstitucional",
        on_delete=models.PROTECT,
        related_name="objetivos_estrategicos",
    )
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(
        max_length=10,
        choices=EstadoCatalogo.choices,
        default=EstadoCatalogo.ACTIVO,
        db_index=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Objetivo estratégico institucional"
        verbose_name_plural = "Objetivos estratégicos institucionales"
        ordering = ["entidad__nombre", "codigo"]
        constraints = [
            models.UniqueConstraint(
                Lower("codigo"),
                "entidad",
                name="uniq_obj_estrategico_entidad_codigo_ci",
            ),
            models.CheckConstraint(
                condition=models.Q(estado__in=EstadoCatalogo.values),
                name="ck_obj_estrategico_estado",
            ),
        ]

    def clean(self):
        super().clean()
        _normalizar_textos(self)

        errores = {}
        if not self.codigo:
            errores["codigo"] = "El código del objetivo es obligatorio."
        if not self.nombre:
            errores["nombre"] = "El nombre del objetivo es obligatorio."
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        _normalizar_textos(self)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class EjePND(models.Model):
    """Eje configurable de un Plan Nacional de Desarrollo."""

    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(
        max_length=10,
        choices=EstadoCatalogo.choices,
        default=EstadoCatalogo.ACTIVO,
        db_index=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Eje PND"
        verbose_name_plural = "Ejes PND"
        ordering = ["codigo"]
        constraints = [
            models.UniqueConstraint(
                Lower("codigo"),
                name="uniq_eje_pnd_codigo_ci",
            ),
            models.CheckConstraint(
                condition=models.Q(estado__in=EstadoCatalogo.values),
                name="ck_eje_pnd_estado",
            ),
        ]

    def clean(self):
        super().clean()
        _normalizar_textos(self)

        errores = {}
        if not self.codigo:
            errores["codigo"] = "El código del eje PND es obligatorio."
        if not self.nombre:
            errores["nombre"] = "El nombre del eje PND es obligatorio."
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        _normalizar_textos(self)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class ObjetivoPND(models.Model):
    """Objetivo configurable perteneciente a un eje PND."""

    eje = models.ForeignKey(
        EjePND,
        on_delete=models.PROTECT,
        related_name="objetivos",
    )
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(
        max_length=10,
        choices=EstadoCatalogo.choices,
        default=EstadoCatalogo.ACTIVO,
        db_index=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Objetivo PND"
        verbose_name_plural = "Objetivos PND"
        ordering = ["eje__codigo", "codigo"]
        constraints = [
            models.UniqueConstraint(
                Lower("codigo"),
                "eje",
                name="uniq_obj_pnd_eje_codigo_ci",
            ),
            models.CheckConstraint(
                condition=models.Q(estado__in=EstadoCatalogo.values),
                name="ck_obj_pnd_estado",
            ),
        ]

    def clean(self):
        super().clean()
        _normalizar_textos(self)

        errores = {}
        if not self.codigo:
            errores["codigo"] = "El código del objetivo PND es obligatorio."
        if not self.nombre:
            errores["nombre"] = "El nombre del objetivo PND es obligatorio."
        if self.eje_id and self.eje.estado != EstadoCatalogo.ACTIVO:
            errores["eje"] = "Solo puede utilizar un eje PND activo."
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        _normalizar_textos(self)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class ODS(models.Model):
    """Objetivo de Desarrollo Sostenible configurable por administradores."""

    numero = models.PositiveSmallIntegerField(
        unique=True,
        validators=[MinValueValidator(1, "El número del ODS debe ser positivo.")],
    )
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(
        max_length=10,
        choices=EstadoCatalogo.choices,
        default=EstadoCatalogo.ACTIVO,
        db_index=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ODS"
        verbose_name_plural = "ODS"
        ordering = ["numero"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(numero__gte=1),
                name="ck_ods_numero_positivo",
            ),
            models.CheckConstraint(
                condition=models.Q(estado__in=EstadoCatalogo.values),
                name="ck_ods_estado",
            ),
        ]

    def clean(self):
        super().clean()
        _normalizar_textos(self, incluye_codigo=False)
        if not self.nombre:
            raise ValidationError({"nombre": "El nombre del ODS es obligatorio."})

    def save(self, *args, **kwargs):
        _normalizar_textos(self, incluye_codigo=False)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"ODS {self.numero} - {self.nombre}"


class Alineacion(models.Model):
    """Vincula un objetivo institucional con un objetivo PND y un ODS."""

    class EstadoAlineacion(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        VALIDADA = "VALIDADA", "Validada"
        RECHAZADA = "RECHAZADA", "Rechazada"

    objetivo_estrategico = models.ForeignKey(
        ObjetivoEstrategico,
        on_delete=models.PROTECT,
        related_name="alineaciones",
    )
    objetivo_pnd = models.ForeignKey(
        ObjetivoPND,
        on_delete=models.PROTECT,
        related_name="alineaciones",
    )
    ods = models.ForeignKey(
        ODS,
        on_delete=models.PROTECT,
        related_name="alineaciones",
    )
    justificacion = models.TextField()
    estado = models.CharField(
        max_length=10,
        choices=EstadoAlineacion.choices,
        default=EstadoAlineacion.BORRADOR,
        db_index=True,
    )
    usuario_creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="alineaciones_creadas",
    )
    usuario_validador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="alineaciones_validadas",
        null=True,
        blank=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Alineación de objetivo"
        verbose_name_plural = "Alineaciones de objetivos"
        ordering = ["-fecha_actualizacion", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["objetivo_estrategico", "objetivo_pnd", "ods"],
                name="uniq_alineacion_obj_pnd_ods",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    estado__in=["BORRADOR", "VALIDADA", "RECHAZADA"]
                ),
                name="ck_alineacion_estado",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        estado="BORRADOR",
                        usuario_validador__isnull=True,
                    )
                    | models.Q(
                        estado__in=["VALIDADA", "RECHAZADA"],
                        usuario_validador__isnull=False,
                    )
                ),
                name="ck_alineacion_validador_estado",
            ),
        ]

    @property
    def entidad_id(self):
        return self.objetivo_estrategico.entidad_id

    @property
    def entidad(self):
        return self.objetivo_estrategico.entidad

    def clean(self):
        super().clean()
        self.justificacion = (self.justificacion or "").strip()
        errores = {}

        if not self.justificacion:
            errores["justificacion"] = "La justificación de la alineación es obligatoria."
        if (
            self.objetivo_estrategico_id
            and self.objetivo_estrategico.estado != EstadoCatalogo.ACTIVO
        ):
            errores["objetivo_estrategico"] = (
                "Solo puede alinear un objetivo estratégico activo."
            )
        if self.objetivo_pnd_id and (
            self.objetivo_pnd.estado != EstadoCatalogo.ACTIVO
            or self.objetivo_pnd.eje.estado != EstadoCatalogo.ACTIVO
        ):
            errores["objetivo_pnd"] = "Solo puede alinear un objetivo PND activo."
        if self.ods_id and self.ods.estado != EstadoCatalogo.ACTIVO:
            errores["ods"] = "Solo puede alinear un ODS activo."

        if self.estado == self.EstadoAlineacion.BORRADOR and self.usuario_validador_id:
            errores["usuario_validador"] = (
                "Una alineación en borrador no puede tener usuario validador."
            )
        if (
            self.estado
            in [self.EstadoAlineacion.VALIDADA, self.EstadoAlineacion.RECHAZADA]
            and not self.usuario_validador_id
        ):
            errores["usuario_validador"] = (
                "La alineación resuelta debe registrar al usuario validador."
            )
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.justificacion = (self.justificacion or "").strip()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.objetivo_estrategico.codigo} / "
            f"{self.objetivo_pnd.codigo} / ODS {self.ods.numero}"
        )
