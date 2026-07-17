from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from .models import EntidadInstitucional, UnidadOrganizacional
from .scope import filtrar_queryset_por_entidad, usuario_puede_acceder_entidad


class EntidadInstitucionalSerializer(serializers.ModelSerializer):
    unidades_count = serializers.SerializerMethodField()

    class Meta:
        model = EntidadInstitucional
        fields = [
            "id",
            "codigo_oficial",
            "nombre",
            "subsector",
            "nivel_gobierno",
            "estado",
            "unidades_count",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "estado",
            "unidades_count",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_unidades_count(self, obj):
        conteo = getattr(obj, "unidades_count", None)
        return conteo if conteo is not None else obj.unidades.count()

    def validate_codigo_oficial(self, value):
        codigo = value.strip().upper()
        if not codigo:
            raise serializers.ValidationError("El código oficial es obligatorio.")
        queryset = EntidadInstitucional.objects.filter(
            codigo_oficial__iexact=codigo
        )
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                "Ya existe una entidad con este código oficial."
            )
        return codigo

    def validate_nombre(self, value):
        nombre = value.strip()
        if not nombre:
            raise serializers.ValidationError(
                "El nombre de la entidad es obligatorio."
            )
        queryset = EntidadInstitucional.objects.filter(nombre__iexact=nombre)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                "Ya existe una entidad con este nombre."
            )
        return nombre

    def validate_subsector(self, value):
        subsector = value.strip()
        if not subsector:
            raise serializers.ValidationError("El subsector es obligatorio.")
        return subsector

    def validate_nivel_gobierno(self, value):
        nivel = value.strip()
        if not nivel:
            raise serializers.ValidationError(
                "El nivel de gobierno es obligatorio."
            )
        return nivel


class UnidadOrganizacionalSerializer(serializers.ModelSerializer):
    entidad_detalle = serializers.SerializerMethodField()
    unidad_padre_detalle = serializers.SerializerMethodField()
    subunidades_count = serializers.SerializerMethodField()

    class Meta:
        model = UnidadOrganizacional
        fields = [
            "id",
            "entidad",
            "entidad_detalle",
            "nombre",
            "codigo",
            "unidad_padre",
            "unidad_padre_detalle",
            "estado",
            "subunidades_count",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "entidad_detalle",
            "unidad_padre_detalle",
            "estado",
            "subunidades_count",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        usuario = getattr(request, "user", None)
        self.fields["entidad"].queryset = filtrar_queryset_por_entidad(
            EntidadInstitucional.objects.all(),
            usuario,
            "pk",
        )
        self.fields["unidad_padre"].queryset = filtrar_queryset_por_entidad(
            UnidadOrganizacional.objects.filter(
                estado=UnidadOrganizacional.Estado.ACTIVA
            ),
            usuario,
        )

    def get_entidad_detalle(self, obj):
        return {
            "id": obj.entidad_id,
            "codigo_oficial": obj.entidad.codigo_oficial,
            "nombre": obj.entidad.nombre,
        }

    def get_unidad_padre_detalle(self, obj):
        if obj.unidad_padre_id is None:
            return None
        return {
            "id": obj.unidad_padre_id,
            "codigo": obj.unidad_padre.codigo,
            "nombre": obj.unidad_padre.nombre,
        }

    def get_subunidades_count(self, obj):
        conteo = getattr(obj, "subunidades_count", None)
        return conteo if conteo is not None else obj.subunidades.count()

    def validate_nombre(self, value):
        nombre = value.strip()
        if not nombre:
            raise serializers.ValidationError(
                "El nombre de la unidad es obligatorio."
            )
        return nombre

    def validate_codigo(self, value):
        return value.strip().upper() if value else ""

    def validate_entidad(self, entidad):
        request = self.context.get("request")
        usuario = getattr(request, "user", None)
        if not usuario_puede_acceder_entidad(usuario, entidad.pk):
            raise PermissionDenied(
                "No puede gestionar unidades de otra entidad institucional."
            )
        if entidad.estado != EntidadInstitucional.Estado.ACTIVA:
            raise serializers.ValidationError(
                "No se pueden registrar unidades en una entidad inactiva."
            )
        if self.instance and self.instance.entidad_id != entidad.pk:
            raise serializers.ValidationError(
                "No se puede cambiar la entidad de una unidad existente."
            )
        return entidad

    def validate(self, attrs):
        entidad = attrs.get("entidad", getattr(self.instance, "entidad", None))
        nombre = attrs.get("nombre", getattr(self.instance, "nombre", ""))
        codigo = attrs.get("codigo", getattr(self.instance, "codigo", ""))
        unidad_padre = attrs.get(
            "unidad_padre",
            getattr(self.instance, "unidad_padre", None),
        )

        if entidad is None:
            return attrs

        duplicada = UnidadOrganizacional.objects.filter(
            entidad=entidad,
            nombre__iexact=nombre,
        )
        if self.instance:
            duplicada = duplicada.exclude(pk=self.instance.pk)
        if duplicada.exists():
            raise serializers.ValidationError(
                {"nombre": "Ya existe una unidad con este nombre en la entidad."}
            )

        if codigo:
            codigo_repetido = UnidadOrganizacional.objects.filter(
                entidad=entidad,
                codigo__iexact=codigo,
            )
            if self.instance:
                codigo_repetido = codigo_repetido.exclude(pk=self.instance.pk)
            if codigo_repetido.exists():
                raise serializers.ValidationError(
                    {"codigo": "Ya existe una unidad con este código en la entidad."}
                )

        if unidad_padre:
            if unidad_padre.entidad_id != entidad.pk:
                raise serializers.ValidationError(
                    {
                        "unidad_padre": (
                            "La unidad superior debe pertenecer a la misma entidad."
                        )
                    }
                )
            if unidad_padre.estado != UnidadOrganizacional.Estado.ACTIVA:
                raise serializers.ValidationError(
                    {"unidad_padre": "La unidad superior debe estar activa."}
                )
            if self.instance and self._genera_ciclo(unidad_padre):
                raise serializers.ValidationError(
                    {
                        "unidad_padre": (
                            "La unidad superior seleccionada genera un ciclo jerárquico."
                        )
                    }
                )

        return attrs

    def _genera_ciclo(self, unidad_padre):
        visitadas = set()
        actual = unidad_padre
        while actual is not None:
            if actual.pk == self.instance.pk:
                return True
            if actual.pk in visitadas:
                return True
            visitadas.add(actual.pk)
            actual = actual.unidad_padre
        return False
