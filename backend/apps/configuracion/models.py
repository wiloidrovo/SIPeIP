from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class EntidadInstitucional(models.Model):
    """Institución a la que pertenecen usuarios y registros de planificación."""

    class Estado(models.TextChoices):
        ACTIVA = "ACTIVA", "Activa"
        INACTIVA = "INACTIVA", "Inactiva"

    codigo_oficial = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200, unique=True)
    subsector = models.CharField(max_length=150)
    nivel_gobierno = models.CharField(max_length=100)
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.ACTIVA,
        db_index=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Entidad institucional"
        verbose_name_plural = "Entidades institucionales"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.codigo_oficial} - {self.nombre}"

    def clean(self):
        super().clean()
        self.codigo_oficial = (self.codigo_oficial or "").strip().upper()
        self.nombre = (self.nombre or "").strip()
        self.subsector = (self.subsector or "").strip()
        self.nivel_gobierno = (self.nivel_gobierno or "").strip()

        errores = {}
        if not self.codigo_oficial:
            errores["codigo_oficial"] = "El código oficial es obligatorio."
        if not self.nombre:
            errores["nombre"] = "El nombre de la entidad es obligatorio."
        if not self.subsector:
            errores["subsector"] = "El subsector es obligatorio."
        if not self.nivel_gobierno:
            errores["nivel_gobierno"] = "El nivel de gobierno es obligatorio."
        codigos_iguales = EntidadInstitucional.objects.filter(
            codigo_oficial__iexact=self.codigo_oficial
        )
        nombres_iguales = EntidadInstitucional.objects.filter(
            nombre__iexact=self.nombre
        )
        if self.pk:
            codigos_iguales = codigos_iguales.exclude(pk=self.pk)
            nombres_iguales = nombres_iguales.exclude(pk=self.pk)
        if self.codigo_oficial and codigos_iguales.exists():
            errores["codigo_oficial"] = (
                "Ya existe una entidad con este código oficial."
            )
        if self.nombre and nombres_iguales.exists():
            errores["nombre"] = "Ya existe una entidad con este nombre."
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.codigo_oficial = (self.codigo_oficial or "").strip().upper()
        self.nombre = (self.nombre or "").strip()
        self.subsector = (self.subsector or "").strip()
        self.nivel_gobierno = (self.nivel_gobierno or "").strip()
        return super().save(*args, **kwargs)


class UnidadOrganizacional(models.Model):
    """Unidad jerárquica que pertenece a una única entidad institucional."""

    class Estado(models.TextChoices):
        ACTIVA = "ACTIVA", "Activa"
        INACTIVA = "INACTIVA", "Inactiva"

    entidad = models.ForeignKey(
        EntidadInstitucional,
        on_delete=models.PROTECT,
        related_name="unidades",
    )
    nombre = models.CharField(max_length=150)
    codigo = models.CharField(max_length=50, blank=True)
    unidad_padre = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="subunidades",
        null=True,
        blank=True,
    )
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.ACTIVA,
        db_index=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Unidad organizacional"
        verbose_name_plural = "Unidades organizacionales"
        ordering = ["entidad__nombre", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["entidad", "nombre"],
                name="unique_unidad_nombre_por_entidad",
            ),
            models.UniqueConstraint(
                fields=["entidad", "codigo"],
                condition=~Q(codigo=""),
                name="unique_unidad_codigo_por_entidad",
            ),
        ]

    def __str__(self):
        return f"{self.entidad.codigo_oficial} - {self.nombre}"

    def clean(self):
        super().clean()
        self.nombre = (self.nombre or "").strip()
        self.codigo = (self.codigo or "").strip().upper()

        errores = {}
        if not self.nombre:
            errores["nombre"] = "El nombre de la unidad es obligatorio."

        if self.unidad_padre_id:
            if self.entidad_id != self.unidad_padre.entidad_id:
                errores["unidad_padre"] = (
                    "La unidad superior debe pertenecer a la misma entidad."
                )
            elif self.pk and self.unidad_padre_id == self.pk:
                errores["unidad_padre"] = (
                    "Una unidad no puede ser su propia unidad superior."
                )
            elif self._genera_ciclo(self.unidad_padre):
                errores["unidad_padre"] = (
                    "La unidad superior seleccionada genera un ciclo jerárquico."
                )

        if self.entidad_id and self.nombre:
            nombres_iguales = UnidadOrganizacional.objects.filter(
                entidad_id=self.entidad_id,
                nombre__iexact=self.nombre,
            )
            if self.pk:
                nombres_iguales = nombres_iguales.exclude(pk=self.pk)
            if nombres_iguales.exists():
                errores["nombre"] = (
                    "Ya existe una unidad con este nombre en la entidad."
                )
        if self.entidad_id and self.codigo:
            codigos_iguales = UnidadOrganizacional.objects.filter(
                entidad_id=self.entidad_id,
                codigo__iexact=self.codigo,
            )
            if self.pk:
                codigos_iguales = codigos_iguales.exclude(pk=self.pk)
            if codigos_iguales.exists():
                errores["codigo"] = (
                    "Ya existe una unidad con este código en la entidad."
                )

        if errores:
            raise ValidationError(errores)

    def _genera_ciclo(self, unidad_padre):
        visitadas = set()
        actual = unidad_padre
        while actual is not None:
            if self.pk and actual.pk == self.pk:
                return True
            if actual.pk in visitadas:
                return True
            visitadas.add(actual.pk)
            actual = actual.unidad_padre
        return False

    def save(self, *args, **kwargs):
        self.nombre = (self.nombre or "").strip()
        self.codigo = (self.codigo or "").strip().upper()
        return super().save(*args, **kwargs)
