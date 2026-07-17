from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    """Valida las credenciales recibidas por el inicio de sesión."""

    username = serializers.CharField(
        max_length=150,
        trim_whitespace=True,
        error_messages={
            "blank": "El nombre de usuario es obligatorio.",
            "max_length": "El nombre de usuario no puede superar los 150 caracteres.",
            "required": "El nombre de usuario es obligatorio.",
        },
    )
    password = serializers.CharField(
        allow_blank=False,
        max_length=128,
        trim_whitespace=False,
        write_only=True,
        error_messages={
            "blank": "La contraseña es obligatoria.",
            "max_length": "La contraseña no puede superar los 128 caracteres.",
            "required": "La contraseña es obligatoria.",
        },
    )


class UsuarioSesionSerializer(serializers.Serializer):
    """Representación segura de la identidad y permisos de la sesión actual."""

    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    nombre_completo = serializers.SerializerMethodField()
    estado = serializers.CharField(read_only=True)
    rol = serializers.SerializerMethodField()
    permisos = serializers.SerializerMethodField()
    institucion = serializers.SerializerMethodField()
    unidad = serializers.SerializerMethodField()
    es_superusuario = serializers.BooleanField(source="is_superuser", read_only=True)

    def get_nombre_completo(self, obj):
        nombre_completo = obj.get_full_name().strip()
        return nombre_completo or obj.username

    def get_rol(self, obj):
        if obj.rol is None:
            return None

        return {
            "id": obj.rol_id,
            "codigo": obj.rol.codigo,
            "nombre": obj.rol.nombre,
            "activo": obj.rol.activo,
            "alcance": obj.rol.alcance,
        }

    def get_permisos(self, obj):
        return sorted(set(obj.get_sipeip_permissions()))

    def get_institucion(self, obj):
        if not obj.entidad_id:
            return None
        return {
            "id": obj.entidad_id,
            "codigo_oficial": obj.entidad.codigo_oficial,
            "nombre": obj.entidad.nombre,
        }

    def get_unidad(self, obj):
        if not obj.unidad_organizacional_id:
            return None
        return {
            "id": obj.unidad_organizacional_id,
            "codigo": obj.unidad_organizacional.codigo,
            "nombre": obj.unidad_organizacional.nombre,
        }
