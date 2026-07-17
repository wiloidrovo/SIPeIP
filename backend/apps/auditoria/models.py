from django.conf import settings
from django.db import models


class EventoAuditoria(models.Model):
    class Resultado(models.TextChoices):
        EXITO = "EXITO", "Éxito"
        FALLO = "FALLO", "Fallo"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="eventos_auditoria",
        null=True,
        blank=True,
    )
    usuario_identificador = models.CharField(max_length=150, blank=True)
    entidad = models.ForeignKey(
        "configuracion.EntidadInstitucional",
        on_delete=models.PROTECT,
        related_name="eventos_auditoria",
        null=True,
        blank=True,
    )
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True)
    modulo = models.CharField(max_length=60, db_index=True)
    funcionalidad = models.CharField(max_length=120)
    accion = models.CharField(max_length=60, db_index=True)
    tipo_entidad = models.CharField(max_length=120, blank=True)
    registro_id = models.CharField(max_length=64, blank=True)
    valores_anteriores = models.JSONField(default=dict, blank=True)
    valores_posteriores = models.JSONField(default=dict, blank=True)
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    resultado = models.CharField(
        max_length=10,
        choices=Resultado.choices,
        default=Resultado.EXITO,
        db_index=True,
    )
    detalle = models.TextField(blank=True)

    class Meta:
        verbose_name = "Evento de auditoría"
        verbose_name_plural = "Eventos de auditoría"
        ordering = ["-fecha_hora", "-id"]
        indexes = [
            models.Index(fields=["modulo", "accion", "fecha_hora"]),
            models.Index(fields=["entidad", "fecha_hora"]),
        ]

    def __str__(self):
        return f"{self.modulo}: {self.accion} ({self.resultado})"
