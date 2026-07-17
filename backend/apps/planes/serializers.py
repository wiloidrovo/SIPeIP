from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.configuracion.models import EntidadInstitucional
from apps.configuracion.scope import usuario_puede_acceder_entidad
from apps.usuarios.models import Usuario

from .models import HistorialEstadoPlan, Plan


class HistorialEstadoPlanSerializer(serializers.ModelSerializer):
    usuario_detalle = serializers.SerializerMethodField()

    class Meta:
        model = HistorialEstadoPlan
        fields = [
            "id",
            "accion",
            "estado_anterior",
            "estado_nuevo",
            "observacion",
            "usuario",
            "usuario_detalle",
            "fecha",
        ]
        read_only_fields = fields

    def get_usuario_detalle(self, obj):
        return {
            "id": obj.usuario_id,
            "username": obj.usuario.username,
            "nombre_completo": obj.usuario.get_full_name().strip()
            or obj.usuario.username,
        }


class TransicionPlanSerializer(serializers.Serializer):
    observacion = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        trim_whitespace=True,
    )

    def validate_observacion(self, value):
        if self.context.get("observacion_requerida") and not value.strip():
            raise serializers.ValidationError(
                "La observación es obligatoria para esta acción."
            )
        return value.strip()

    def validate(self, attrs):
        if self.context.get("observacion_requerida") and not attrs.get(
            "observacion", ""
        ):
            raise serializers.ValidationError(
                {"observacion": "La observación es obligatoria para esta acción."}
            )
        return attrs


class PlanSerializer(serializers.ModelSerializer):
    """
    Serializador principal para planes institucionales.

    Expone el identificador del responsable para operaciones de escritura y
    una representación resumida para lectura desde el frontend.
    """

    entidad = serializers.PrimaryKeyRelatedField(
        queryset=EntidadInstitucional.objects.all(),
        required=False,
        allow_null=False,
    )
    responsable = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(),
        required=False,
        allow_null=True,
    )
    responsable_detalle = serializers.SerializerMethodField()
    entidad_detalle = serializers.SerializerMethodField()
    creado_por_detalle = serializers.SerializerMethodField()
    historial_count = serializers.SerializerMethodField()
    ultima_observacion = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            "id",
            "nombre",
            "descripcion",
            "entidad",
            "entidad_detalle",
            "periodo_inicio",
            "periodo_fin",
            "responsable",
            "responsable_detalle",
            "creado_por",
            "creado_por_detalle",
            "historial_count",
            "ultima_observacion",
            "estado",
            "activo",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "responsable_detalle",
            "entidad_detalle",
            "creado_por",
            "creado_por_detalle",
            "historial_count",
            "ultima_observacion",
            "estado",
            "activo",
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

    def get_entidad_detalle(self, obj):
        if not obj.entidad_id:
            return None
        return {
            "id": obj.entidad_id,
            "codigo_oficial": obj.entidad.codigo_oficial,
            "nombre": obj.entidad.nombre,
        }

    def get_creado_por_detalle(self, obj):
        if not obj.creado_por_id:
            return None
        return {
            "id": obj.creado_por_id,
            "username": obj.creado_por.username,
            "nombre_completo": obj.creado_por.get_full_name().strip()
            or obj.creado_por.username,
        }

    def get_historial_count(self, obj):
        return len(obj.historial_estados.all())

    def get_ultima_observacion(self, obj):
        evento = next(iter(obj.historial_estados.all()), None)
        if evento is None or not evento.observacion:
            return None
        return {
            "accion": evento.accion,
            "observacion": evento.observacion,
            "fecha": evento.fecha,
        }

    def validate_entidad(self, value):
        request = self.context.get("request")
        actor = getattr(request, "user", None)
        if self.instance and self.instance.entidad_id != value.pk:
            raise serializers.ValidationError(
                "La entidad del plan no puede modificarse una vez creado."
            )
        if value and not usuario_puede_acceder_entidad(actor, value.pk):
            raise PermissionDenied(
                "No puede gestionar planes de otra entidad institucional."
            )
        if value and value.estado != EntidadInstitucional.Estado.ACTIVA:
            raise serializers.ValidationError(
                "No se pueden registrar planes en una entidad inactiva."
            )
        return value

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

        if value and (
            not value.is_active
            or value.estado != Usuario.EstadoUsuario.ACTIVO
        ):
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
        entidad = attrs.get("entidad", getattr(self.instance, "entidad", None))
        responsable = attrs.get(
            "responsable", getattr(self.instance, "responsable", None)
        )

        if responsable and entidad and responsable.entidad_id != entidad.pk:
            raise serializers.ValidationError(
                {
                    "responsable": (
                        "El responsable debe pertenecer a la entidad del plan."
                    )
                }
            )

        if entidad:
            duplicado = Plan.objects.filter(
                entidad=entidad,
                nombre__iexact=attrs.get(
                    "nombre", getattr(self.instance, "nombre", "")
                ),
            )
            if self.instance:
                duplicado = duplicado.exclude(pk=self.instance.pk)
            if duplicado.exists():
                raise serializers.ValidationError(
                    {"nombre": "Ya existe un plan con este nombre en la entidad."}
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
