from rest_framework import serializers

from .models import EventoAuditoria


class EventoAuditoriaSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(
        source="usuario.get_full_name",
        read_only=True,
    )
    entidad_nombre = serializers.CharField(source="entidad.nombre", read_only=True)

    class Meta:
        model = EventoAuditoria
        fields = [
            "id",
            "usuario",
            "usuario_identificador",
            "usuario_nombre",
            "entidad",
            "entidad_nombre",
            "fecha_hora",
            "modulo",
            "funcionalidad",
            "accion",
            "tipo_entidad",
            "registro_id",
            "valores_anteriores",
            "valores_posteriores",
            "direccion_ip",
            "resultado",
            "detalle",
        ]
        read_only_fields = fields
