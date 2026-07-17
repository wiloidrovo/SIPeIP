from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.configuracion.models import EntidadInstitucional, UnidadOrganizacional
from apps.configuracion.scope import (
    obtener_alcance_usuario,
    usuario_puede_acceder_entidad,
)
from apps.roles.models import Rol
from apps.roles.permissions import alcance_es_delegable, es_rol_tecnico_protegido
from apps.roles.serializers import RolResumenSerializer

from .models import Usuario
import re


class UsuarioSerializer(serializers.ModelSerializer):
    """
    Serializador principal para la gestión de Usuarios.
    Maneja la creación y actualización segura de contraseñas y la sincronización de estados.
    """
    rol_detalle = RolResumenSerializer(source="rol", read_only=True)
    entidad_detalle = serializers.SerializerMethodField()
    unidad_organizacional_detalle = serializers.SerializerMethodField()
    email = serializers.EmailField(
        required=True,
        allow_blank=False,
        error_messages={
            "required": "El correo es obligatorio.",
            "blank": "El correo es obligatorio.",
            "invalid": "Ingrese un correo válido.",
        },
    )

    # El password solo se puede escribir, nunca se incluye en las respuestas GET.
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        min_length=8,
        error_messages={
            "min_length": "La contraseña debe tener al menos 8 caracteres.",
            "blank": "La contraseña es obligatoria.",
        },
    )

    rol = serializers.PrimaryKeyRelatedField(
        queryset=Rol.objects.filter(activo=True),
        required=True,
        allow_null=False,
        error_messages={
            "required": "Debe seleccionar un rol.",
            "null": "Debe seleccionar un rol.",
            "does_not_exist": "El rol seleccionado no existe o no está activo.",
            "incorrect_type": "El rol seleccionado no es válido.",
        },
    )

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "rol",
            "rol_detalle",
            "estado",
            "telefono",
            "entidad",
            "entidad_detalle",
            "unidad_organizacional",
            "unidad_organizacional_detalle",
            "is_active",
            "is_staff",
            "date_joined",
        ]
        # Campos gestionados internamente o mediante endpoints de estado.
        read_only_fields = [
            "id",
            "date_joined",
            "rol_detalle",
            "entidad_detalle",
            "unidad_organizacional_detalle",
            "estado",
            "is_active",
            "is_staff",
        ]

    def get_entidad_detalle(self, obj):
        if not obj.entidad_id:
            return None
        return {
            "id": obj.entidad_id,
            "codigo_oficial": obj.entidad.codigo_oficial,
            "nombre": obj.entidad.nombre,
        }

    def get_unidad_organizacional_detalle(self, obj):
        if not obj.unidad_organizacional_id:
            return None
        return {
            "id": obj.unidad_organizacional_id,
            "codigo": obj.unidad_organizacional.codigo,
            "nombre": obj.unidad_organizacional.nombre,
        }

    def validate_entidad(self, value):
        request = self.context.get("request")
        actor = getattr(request, "user", None)
        if value and not usuario_puede_acceder_entidad(actor, value.pk):
            raise PermissionDenied(
                "No puede asignar usuarios a otra entidad institucional."
            )
        if value and value.estado != EntidadInstitucional.Estado.ACTIVA:
            raise serializers.ValidationError(
                "No se puede asignar una entidad institucional inactiva."
            )
        return value

    def validate_unidad_organizacional(self, value):
        if value and value.estado != UnidadOrganizacional.Estado.ACTIVA:
            raise serializers.ValidationError(
                "No se puede asignar una unidad organizacional inactiva."
            )
        return value

    def validate_username(self, value):
        """Valida que el nombre de usuario no esté vacío y sea único."""
        username = value.strip()

        if not username:
            raise serializers.ValidationError("El nombre de usuario es obligatorio.")

        queryset = Usuario.objects.filter(username__iexact=username)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError("Ya existe un usuario con este nombre.")

        return username

    def validate_email(self, value):
        """Asegura unicidad del correo ignorando mayúsculas/minúsculas."""
        email = value.strip().lower()

        queryset = Usuario.objects.filter(email__iexact=email)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError("Ya existe un usuario con este correo.")

        return email

    def validate_first_name(self, value):
        return value.strip() if value else ""

    def validate_last_name(self, value):
        return value.strip() if value else ""

    def validate_telefono(self, value):
        """Aplica validación de formato para celular ecuatoriano (10 dígitos, inicia en 09)."""
        telefono = value.strip() if value else ""

        if not telefono:
            return ""

        if not re.fullmatch(r"09\d{8}", telefono):
            raise serializers.ValidationError(
                "Ingrese un número celular ecuatoriano válido: debe tener 10 dígitos e iniciar con 09."
            )

        return telefono

    def validate_rol(self, value):
        """Impide asignar un rol que actualmente esté desactivado."""
        if value and not value.activo:
            raise serializers.ValidationError("No se puede asignar un rol inactivo.")

        request = self.context.get("request")
        actor = getattr(request, "user", None)
        if value and es_rol_tecnico_protegido(value) and not getattr(
            actor, "is_superuser", False
        ):
            raise PermissionDenied(
                "Solo un superusuario puede asignar un rol técnico de acceso total."
            )

        if value and not getattr(actor, "is_superuser", False):
            obtener_permisos = getattr(actor, "get_sipeip_permissions", None)
            permisos_actor = set(obtener_permisos()) if obtener_permisos else set()
            permisos_destino = set(value.permisos)
            if not permisos_destino.issubset(permisos_actor):
                raise PermissionDenied(
                    "No puede asignar un rol con permisos superiores a los propios."
                )

            alcance_actor = obtener_alcance_usuario(actor)
            if not alcance_es_delegable(alcance_actor, value.alcance):
                raise PermissionDenied(
                    "No puede asignar un rol con un alcance superior o distinto al propio."
                )

        if (
            self.instance
            and getattr(actor, "pk", None) == self.instance.pk
            and self.instance.rol_id != value.pk
            and not actor.is_superuser
        ):
            raise PermissionDenied("No puede cambiar su propio rol.")

        return value

    def validate(self, attrs):
        request = self.context.get("request")
        password = attrs.get("password")
        entidad = attrs.get("entidad", getattr(self.instance, "entidad", None))
        unidad = attrs.get(
            "unidad_organizacional",
            getattr(self.instance, "unidad_organizacional", None),
        )
        rol = attrs.get("rol", getattr(self.instance, "rol", None))

        if (
            rol
            and rol.alcance not in {Rol.Alcance.TOTAL, Rol.Alcance.GLOBAL}
            and entidad is None
        ):
            raise serializers.ValidationError(
                {"entidad": "Este rol requiere una entidad institucional asignada."}
            )

        if unidad and (entidad is None or unidad.entidad_id != entidad.pk):
            raise serializers.ValidationError(
                {
                    "unidad_organizacional": (
                        "La unidad organizacional debe pertenecer a la entidad asignada."
                    )
                }
            )

        if self.instance and (
            self.instance.is_staff
            or self.instance.is_superuser
            or es_rol_tecnico_protegido(self.instance.rol)
        ):
            actor = getattr(request, "user", None)

            if not getattr(actor, "is_superuser", False):
                raise PermissionDenied(
                    "Solo un superusuario puede modificar una cuenta administrativa."
                )

        if request and request.method == "POST" and not password:
            raise serializers.ValidationError(
                {"password": "La contraseña es obligatoria al registrar un usuario."}
            )

        if password:
            candidato = Usuario(
                username=attrs.get(
                    "username", getattr(self.instance, "username", "")
                ),
                email=attrs.get("email", getattr(self.instance, "email", "")),
                first_name=attrs.get(
                    "first_name", getattr(self.instance, "first_name", "")
                ),
                last_name=attrs.get(
                    "last_name", getattr(self.instance, "last_name", "")
                ),
            )
            validate_password(password, user=candidato)

        return attrs

    def _sincronizar_estado_activo(self, usuario):
        """
        Sincroniza el campo `estado` (custom) con `is_active` (Django auth) 
        para asegurar que el usuario no pueda iniciar sesión si está inactivo/bloqueado.
        """
        if usuario.estado == Usuario.EstadoUsuario.ACTIVO:
            usuario.is_active = True

        if usuario.estado in [
            Usuario.EstadoUsuario.INACTIVO,
            Usuario.EstadoUsuario.BLOQUEADO,
        ]:
            usuario.is_active = False

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        usuario = Usuario(**validated_data)

        self._sincronizar_estado_activo(usuario)

        if password:
            usuario.set_password(password)
        else:
            usuario.set_unusable_password()

        usuario.save()
        return usuario

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        self._sincronizar_estado_activo(instance)

        if password:
            instance.set_password(password)

        instance.save()
        return instance
