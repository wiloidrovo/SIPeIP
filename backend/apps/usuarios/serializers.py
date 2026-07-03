from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from apps.roles.models import Rol
from apps.roles.serializers import RolSerializer
from .models import Usuario
import re


class UsuarioSerializer(serializers.ModelSerializer):
    """
    Serializador principal para la gestión de Usuarios.
    Maneja la creación y actualización segura de contraseñas y la sincronización de estados.
    """
    rol_detalle = RolSerializer(source="rol", read_only=True)
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
            "is_active",
            "is_staff",
            "date_joined",
        ]
        # Campos gestionados internamente o mediante endpoints de estado.
        read_only_fields = [
            "id",
            "date_joined",
            "rol_detalle",
        ]

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

        return value

    def validate(self, attrs):
        request = self.context.get("request")
        password = attrs.get("password")

        if request and request.method == "POST" and not password:
            raise serializers.ValidationError(
                {"password": "La contraseña es obligatoria al registrar un usuario."}
            )

        if password:
            validate_password(password)

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