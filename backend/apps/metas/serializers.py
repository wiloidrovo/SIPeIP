from rest_framework import serializers

from apps.planes.models import Plan
from apps.usuarios.models import Usuario

from .models import AvanceIndicador, Indicador, Meta


class MetaSerializer(serializers.ModelSerializer):
    """
    Serializador para metas institucionales.

    Permite asociar una meta a un plan y expone una representación resumida del
    plan para facilitar su consumo desde la interfaz.
    """

    plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.all())
    plan_detalle = serializers.SerializerMethodField()
    indicadores_count = serializers.SerializerMethodField()

    class Meta:
        model = Meta
        fields = [
            "id",
            "plan",
            "plan_detalle",
            "nombre",
            "descripcion",
            "resultado_esperado",
            "fecha_inicio",
            "fecha_fin",
            "estado",
            "activa",
            "indicadores_count",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "plan_detalle",
            "indicadores_count",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_plan_detalle(self, obj):
        """Devuelve información básica del plan asociado."""

        return {
            "id": obj.plan.id,
            "nombre": obj.plan.nombre,
            "estado": obj.plan.estado,
        }

    def get_indicadores_count(self, obj):
        """Devuelve el número de indicadores asociados a la meta."""

        return obj.indicadores.count()

    def validate_nombre(self, value):
        """Normaliza y valida el nombre de la meta."""

        nombre = value.strip()

        if not nombre:
            raise serializers.ValidationError("El nombre de la meta es obligatorio.")

        if len(nombre) < 3:
            raise serializers.ValidationError(
                "El nombre de la meta debe tener al menos 3 caracteres."
            )

        return nombre

    def validate_descripcion(self, value):
        """Normaliza la descripción de la meta."""

        return value.strip() if value else ""

    def validate_resultado_esperado(self, value):
        """Normaliza el resultado esperado de la meta."""

        return value.strip() if value else ""

    def validate_plan(self, value):
        """Evita asociar metas a planes inactivos o archivados."""

        if not value.activo or value.estado == Plan.EstadoPlan.ARCHIVADO:
            raise serializers.ValidationError(
                "No se puede registrar una meta en un plan inactivo o archivado."
            )

        return value

    def validate(self, attrs):
        """Valida la coherencia del rango de fechas de la meta."""

        fecha_inicio = attrs.get("fecha_inicio", getattr(self.instance, "fecha_inicio", None))
        fecha_fin = attrs.get("fecha_fin", getattr(self.instance, "fecha_fin", None))

        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError(
                {
                    "fecha_fin": (
                        "La fecha de finalización no puede ser anterior "
                        "a la fecha de inicio."
                    )
                }
            )

        return attrs


class IndicadorSerializer(serializers.ModelSerializer):
    """
    Serializador para indicadores de cumplimiento.

    El indicador queda asociado a una meta y conserva valores base, meta y
    actual para seguimiento periódico.
    """

    meta = serializers.PrimaryKeyRelatedField(queryset=Meta.objects.all())
    meta_detalle = serializers.SerializerMethodField()
    avances_count = serializers.SerializerMethodField()

    class Meta:
        model = Indicador
        fields = [
            "id",
            "meta",
            "meta_detalle",
            "nombre",
            "descripcion",
            "unidad_medida",
            "valor_base",
            "valor_meta",
            "valor_actual",
            "frecuencia",
            "activo",
            "avances_count",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "meta_detalle",
            "valor_actual",
            "avances_count",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_meta_detalle(self, obj):
        """Devuelve información básica de la meta asociada."""

        return {
            "id": obj.meta.id,
            "nombre": obj.meta.nombre,
            "plan": obj.meta.plan.nombre,
        }

    def get_avances_count(self, obj):
        """Devuelve el número de avances registrados para el indicador."""

        return obj.avances.count()

    def validate_nombre(self, value):
        """Normaliza y valida el nombre del indicador."""

        nombre = value.strip()

        if not nombre:
            raise serializers.ValidationError(
                "El nombre del indicador es obligatorio."
            )

        if len(nombre) < 3:
            raise serializers.ValidationError(
                "El nombre del indicador debe tener al menos 3 caracteres."
            )

        return nombre

    def validate_descripcion(self, value):
        """Normaliza la descripción del indicador."""

        return value.strip() if value else ""

    def validate_unidad_medida(self, value):
        """Valida la unidad de medida del indicador."""

        unidad = value.strip()

        if not unidad:
            raise serializers.ValidationError("La unidad de medida es obligatoria.")

        return unidad

    def validate_meta(self, value):
        """Evita crear indicadores sobre metas archivadas o inactivas."""

        if not value.activa or value.estado == Meta.EstadoMeta.ARCHIVADA:
            raise serializers.ValidationError(
                "No se puede registrar un indicador en una meta inactiva o archivada."
            )

        return value

    def validate_valor_base(self, value):
        """Valida que el valor base no sea negativo."""

        if value < 0:
            raise serializers.ValidationError("El valor base no puede ser negativo.")

        return value

    def validate_valor_meta(self, value):
        """Valida que el valor meta sea mayor que cero."""

        if value <= 0:
            raise serializers.ValidationError("El valor meta debe ser mayor que cero.")

        return value


class AvanceIndicadorSerializer(serializers.ModelSerializer):
    """
    Serializador para avances de indicadores.

    Cada avance registra un valor medido en una fecha concreta y puede incluir
    una observación para trazabilidad.
    """

    indicador = serializers.PrimaryKeyRelatedField(queryset=Indicador.objects.all())
    indicador_detalle = serializers.SerializerMethodField()
    registrado_por = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(),
        required=False,
        allow_null=True,
    )
    registrado_por_detalle = serializers.SerializerMethodField()

    class Meta:
        model = AvanceIndicador
        fields = [
            "id",
            "indicador",
            "indicador_detalle",
            "fecha_registro",
            "valor",
            "observacion",
            "registrado_por",
            "registrado_por_detalle",
            "fecha_creacion",
        ]
        read_only_fields = [
            "id",
            "indicador_detalle",
            "registrado_por_detalle",
            "fecha_creacion",
        ]

    def get_indicador_detalle(self, obj):
        """Devuelve información básica del indicador asociado."""

        return {
            "id": obj.indicador.id,
            "nombre": obj.indicador.nombre,
            "meta": obj.indicador.meta.nombre,
            "unidad_medida": obj.indicador.unidad_medida,
        }

    def get_registrado_por_detalle(self, obj):
        """Devuelve información básica del usuario que registró el avance."""

        if not obj.registrado_por:
            return None

        nombre_completo = (
            f"{obj.registrado_por.first_name} {obj.registrado_por.last_name}"
        ).strip()

        return {
            "id": obj.registrado_por.id,
            "username": obj.registrado_por.username,
            "nombre_completo": nombre_completo or obj.registrado_por.username,
        }

    def validate_indicador(self, value):
        """Evita registrar avances sobre indicadores inactivos."""

        if not value.activo:
            raise serializers.ValidationError(
                "No se puede registrar avance sobre un indicador inactivo."
            )

        return value

    def validate_observacion(self, value):
        """Normaliza la observación del avance."""

        return value.strip() if value else ""

    def validate_valor(self, value):
        """Valida que el valor registrado no sea negativo."""

        if value < 0:
            raise serializers.ValidationError("El valor del avance no puede ser negativo.")

        return value