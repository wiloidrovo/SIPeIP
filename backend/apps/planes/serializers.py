from rest_framework import serializers

from apps.usuarios.models import Usuario

from .models import Plan


class PlanSerializer(serializers.ModelSerializer):
    """
    Serializador principal para planes institucionales.

    Expone el identificador del responsable para operaciones de escritura y
    una representación resumida para lectura desde el frontend.
    """

    responsable = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(),
        required=False,
        allow_null=True,
    )
    responsable_detalle = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            "id",
            "nombre",
            "descripcion",
            "periodo_inicio",
            "periodo_fin",
            "responsable",
            "responsable_detalle",
            "estado",
            "activo",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "responsable_detalle",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_responsable_detalle(self, obj):
        """Devuelve información básica del usuario responsable del plan."""

        if not obj.responsable:
            return None

        nombre_completo = (
            f"{obj.responsable.first_name} {obj.responsable.last_name}"
        ).strip()

        return {
            "id": obj.responsable.id,
            "username": obj.responsable.username,
            "nombre_completo": nombre_completo or obj.responsable.username,
            "email": obj.responsable.email,
        }

    def validate_nombre(self, value):
        """Normaliza y valida el nombre del plan."""

        nombre = value.strip()

        if not nombre:
            raise serializers.ValidationError("El nombre del plan es obligatorio.")

        if len(nombre) < 3:
            raise serializers.ValidationError(
                "El nombre del plan debe tener al menos 3 caracteres."
            )

        return nombre

    def validate_descripcion(self, value):
        """Normaliza la descripción para evitar espacios innecesarios."""

        return value.strip() if value else ""

    def validate_responsable(self, value):
        """Evita asignar planes a usuarios bloqueados o inactivos."""

        if value and not value.is_active:
            raise serializers.ValidationError(
                "No se puede asignar un plan a un usuario inactivo o bloqueado."
            )

        return value

    def validate(self, attrs):
        """
        Valida la coherencia del rango de fechas del plan.

        La fecha final no puede ser anterior a la fecha inicial, ya que el
        periodo representa la vigencia operativa del plan.
        """

        periodo_inicio = attrs.get(
            "periodo_inicio",
            getattr(self.instance, "periodo_inicio", None),
        )
        periodo_fin = attrs.get(
            "periodo_fin",
            getattr(self.instance, "periodo_fin", None),
        )

        if periodo_inicio and periodo_fin and periodo_fin < periodo_inicio:
            raise serializers.ValidationError(
                {
                    "periodo_fin": (
                        "La fecha de finalización no puede ser anterior "
                        "a la fecha de inicio."
                    )
                }
            )

        return attrs