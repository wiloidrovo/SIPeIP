from rest_framework import serializers

from apps.roles.serializers import RolSerializer

from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    rol_detalle = RolSerializer(source="rol", read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

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

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        usuario = Usuario(**validated_data)

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

        if password:
            instance.set_password(password)

        instance.save()
        return instance