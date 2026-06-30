from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.roles.serializers import RolSerializer

from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    rol_detalle = RolSerializer(source="rol", read_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        min_length=8,
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
        read_only_fields = [
            "id",
            "date_joined",
            "rol_detalle",
        ]

    def validate_username(self, value):
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
        email = value.strip().lower() if value else ""

        if not email:
            return ""

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
        telefono = value.strip() if value else ""

        if telefono and len(telefono) < 7:
            raise serializers.ValidationError("El teléfono debe tener al menos 7 caracteres.")

        return telefono

    def validate_rol(self, value):
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