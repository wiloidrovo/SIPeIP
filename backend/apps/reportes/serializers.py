from rest_framework import serializers

from .datasets import MAX_FILAS_REPORTE


class FiltrosReporteSerializer(serializers.Serializer):
    entidad = serializers.IntegerField(min_value=1, required=False)
    estado = serializers.CharField(max_length=30, required=False, trim_whitespace=True)
    activo = serializers.BooleanField(required=False)
    fecha_desde = serializers.DateField(required=False)
    fecha_hasta = serializers.DateField(required=False)
    buscar = serializers.CharField(max_length=100, required=False, trim_whitespace=True)
    modulo = serializers.CharField(max_length=60, required=False, trim_whitespace=True)
    accion = serializers.CharField(max_length=60, required=False, trim_whitespace=True)
    resultado = serializers.ChoiceField(
        choices=("EXITO", "FALLO"), required=False
    )
    limite = serializers.IntegerField(
        min_value=1,
        max_value=MAX_FILAS_REPORTE,
        required=False,
        default=1000,
    )

    def validate(self, attrs):
        if (
            attrs.get("fecha_desde")
            and attrs.get("fecha_hasta")
            and attrs["fecha_desde"] > attrs["fecha_hasta"]
        ):
            raise serializers.ValidationError(
                {"fecha_hasta": "La fecha hasta no puede ser anterior a la fecha desde."}
            )
        return attrs
