from rest_framework import serializers

from .models import Rol
from .permissions import ALLOWED_ROLE_PERMISSIONS


def normalizar_permisos(value):
    """Valida, limpia y elimina duplicados sin alterar el orden recibido."""

    if value in (None, ""):
        return []

    if not isinstance(value, list):
        raise serializers.ValidationError("Los permisos deben enviarse como una lista.")

    permisos_limpios = []
    for permiso in value:
        if not isinstance(permiso, str):
            raise serializers.ValidationError("Cada permiso debe ser un texto válido.")

        permiso_normalizado = permiso.strip()
        if not permiso_normalizado:
            continue

        if permiso_normalizado not in ALLOWED_ROLE_PERMISSIONS:
            raise serializers.ValidationError(
                f"El permiso '{permiso_normalizado}' no está permitido."
            )

        if permiso_normalizado not in permisos_limpios:
            permisos_limpios.append(permiso_normalizado)

    return permisos_limpios


class RolSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Rol.
    Incluye el conteo de usuarios asignados a este rol de forma virtual.
    """
    usuarios_count = serializers.SerializerMethodField()

    class Meta:
        model = Rol
        fields = [
            "id",
            "codigo",
            "nombre",
            "descripcion",
            "activo",
            "permisos",
            "alcance",
            "usuarios_count",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        # Estado y permisos se gestionan mediante endpoints dedicados, no directamente.
        read_only_fields = [
            "id",
            "codigo",
            "activo",
            "permisos",
            "alcance",
            "usuarios_count",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_usuarios_count(self, obj):
        if hasattr(obj, "usuarios_count_anotado"):
            return obj.usuarios_count_anotado
        return obj.usuarios.count()

    def validate_nombre(self, value):
        """Valida que el nombre no esté vacío."""
        nombre = value.strip()

        if not nombre:
            raise serializers.ValidationError("El nombre del rol es obligatorio.")

        return nombre

    def validate_descripcion(self, value):
        return value.strip() if value else ""

    def validate_permisos(self, value):
        """Valida que los permisos proporcionados pertenezcan al catálogo del sistema."""
        return normalizar_permisos(value)


class AsignarPermisosRolSerializer(serializers.Serializer):
    """Entrada exclusiva de la acción protegida de asignación de permisos."""

    permisos = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        allow_empty=True,
    )

    def validate_permisos(self, value):
        return normalizar_permisos(value)


class ConfigurarAlcanceRolSerializer(serializers.Serializer):
    alcance = serializers.ChoiceField(
        choices=Rol.Alcance.choices,
        error_messages={
            "invalid_choice": "El alcance seleccionado no es válido.",
            "required": "El alcance es obligatorio.",
        },
    )


class RolResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = [
            "id",
            "codigo",
            "nombre",
            "activo",
        ]
        read_only_fields = fields
