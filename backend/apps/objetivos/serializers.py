from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.configuracion.models import EntidadInstitucional
from apps.roles.models import Rol

from .models import Alineacion, EjePND, EstadoCatalogo, ObjetivoEstrategico, ObjetivoPND, ODS


def _validar_entidad_en_alcance(request, entidad_id):
    """Impide ampliar el alcance institucional mediante IDs del payload."""

    usuario = getattr(request, "user", None)
    if not usuario or not usuario.is_authenticated:
        raise PermissionDenied("Debe autenticarse para operar sobre una entidad.")

    if usuario.is_superuser and usuario.is_active:
        return

    rol = getattr(usuario, "rol", None)
    if not rol or not rol.activo:
        raise PermissionDenied("No tiene un rol activo para realizar esta acción.")

    if rol.alcance in {Rol.Alcance.TOTAL, Rol.Alcance.GLOBAL}:
        return

    if getattr(usuario, "entidad_id", None) != entidad_id:
        raise PermissionDenied(
            "No tiene acceso a registros de otra entidad institucional."
        )


def _resumen_entidad(entidad):
    return {
        "id": entidad.pk,
        "codigo_oficial": entidad.codigo_oficial,
        "nombre": entidad.nombre,
    }


def _resumen_usuario(usuario):
    if usuario is None:
        return None
    nombre = usuario.get_full_name().strip()
    return {
        "id": usuario.pk,
        "username": usuario.username,
        "nombre_completo": nombre or usuario.username,
    }


class _CatalogoTextoSerializer(serializers.ModelSerializer):
    """Validaciones comunes de los catálogos codificados."""

    def validate_codigo(self, value):
        codigo = value.strip().upper()
        if not codigo:
            raise serializers.ValidationError("El código es obligatorio.")
        return codigo

    def validate_nombre(self, value):
        nombre = value.strip()
        if not nombre:
            raise serializers.ValidationError("El nombre es obligatorio.")
        return nombre

    def validate_descripcion(self, value):
        return value.strip() if value else ""


class ObjetivoEstrategicoSerializer(_CatalogoTextoSerializer):
    entidad = serializers.PrimaryKeyRelatedField(
        queryset=EntidadInstitucional.objects.all()
    )
    entidad_detalle = serializers.SerializerMethodField()

    class Meta:
        model = ObjetivoEstrategico
        fields = [
            "id",
            "entidad",
            "entidad_detalle",
            "codigo",
            "nombre",
            "descripcion",
            "estado",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "entidad_detalle",
            "estado",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_entidad_detalle(self, obj):
        return _resumen_entidad(obj.entidad)

    def validate(self, attrs):
        instance = self.instance
        entidad = attrs.get("entidad", getattr(instance, "entidad", None))
        codigo = attrs.get("codigo", getattr(instance, "codigo", None))

        if entidad is not None:
            _validar_entidad_en_alcance(self.context.get("request"), entidad.pk)
            if getattr(entidad, "estado", None) != "ACTIVA":
                raise serializers.ValidationError(
                    {"entidad": "Solo puede utilizar una entidad institucional activa."}
                )

        if instance and entidad and entidad.pk != instance.entidad_id:
            raise serializers.ValidationError(
                {"entidad": "No se puede cambiar la entidad de un objetivo existente."}
            )

        if entidad and codigo:
            duplicados = ObjetivoEstrategico.objects.filter(
                entidad=entidad,
                codigo__iexact=codigo,
            )
            if instance:
                duplicados = duplicados.exclude(pk=instance.pk)
            if duplicados.exists():
                raise serializers.ValidationError(
                    {
                        "codigo": (
                            "Ya existe un objetivo con este código en la entidad."
                        )
                    }
                )

        return attrs


class EjePNDSerializer(_CatalogoTextoSerializer):
    class Meta:
        model = EjePND
        fields = [
            "id",
            "codigo",
            "nombre",
            "descripcion",
            "estado",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "estado",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def validate_codigo(self, value):
        codigo = super().validate_codigo(value)
        duplicados = EjePND.objects.filter(codigo__iexact=codigo)
        if self.instance:
            duplicados = duplicados.exclude(pk=self.instance.pk)
        if duplicados.exists():
            raise serializers.ValidationError(
                "Ya existe un eje PND con este código."
            )
        return codigo


class ObjetivoPNDSerializer(_CatalogoTextoSerializer):
    eje = serializers.PrimaryKeyRelatedField(queryset=EjePND.objects.all())
    eje_detalle = serializers.SerializerMethodField()

    class Meta:
        model = ObjetivoPND
        fields = [
            "id",
            "eje",
            "eje_detalle",
            "codigo",
            "nombre",
            "descripcion",
            "estado",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "eje_detalle",
            "estado",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_eje_detalle(self, obj):
        return {
            "id": obj.eje_id,
            "codigo": obj.eje.codigo,
            "nombre": obj.eje.nombre,
            "estado": obj.eje.estado,
        }

    def validate(self, attrs):
        instance = self.instance
        eje = attrs.get("eje", getattr(instance, "eje", None))
        codigo = attrs.get("codigo", getattr(instance, "codigo", None))

        if eje and eje.estado != EstadoCatalogo.ACTIVO:
            raise serializers.ValidationError(
                {"eje": "Solo puede utilizar un eje PND activo."}
            )

        if instance and eje and eje.pk != instance.eje_id and instance.alineaciones.exists():
            raise serializers.ValidationError(
                {
                    "eje": (
                        "No se puede cambiar el eje de un objetivo PND que ya "
                        "tiene alineaciones."
                    )
                }
            )

        if eje and codigo:
            duplicados = ObjetivoPND.objects.filter(
                eje=eje,
                codigo__iexact=codigo,
            )
            if instance:
                duplicados = duplicados.exclude(pk=instance.pk)
            if duplicados.exists():
                raise serializers.ValidationError(
                    {"codigo": "Ya existe este código de objetivo dentro del eje PND."}
                )

        return attrs


class ODSSerializer(serializers.ModelSerializer):
    class Meta:
        model = ODS
        fields = [
            "id",
            "numero",
            "nombre",
            "descripcion",
            "estado",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "estado",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def validate_numero(self, value):
        if value < 1:
            raise serializers.ValidationError("El número del ODS debe ser positivo.")
        duplicados = ODS.objects.filter(numero=value)
        if self.instance:
            duplicados = duplicados.exclude(pk=self.instance.pk)
        if duplicados.exists():
            raise serializers.ValidationError("Ya existe un ODS con este número.")
        return value

    def validate_nombre(self, value):
        nombre = value.strip()
        if not nombre:
            raise serializers.ValidationError("El nombre del ODS es obligatorio.")
        return nombre

    def validate_descripcion(self, value):
        return value.strip() if value else ""


class AlineacionSerializer(serializers.ModelSerializer):
    entidad = serializers.IntegerField(
        source="objetivo_estrategico.entidad_id",
        read_only=True,
    )
    entidad_detalle = serializers.SerializerMethodField()
    objetivo_estrategico_detalle = serializers.SerializerMethodField()
    objetivo_pnd_detalle = serializers.SerializerMethodField()
    ods_detalle = serializers.SerializerMethodField()
    usuario_creador = serializers.PrimaryKeyRelatedField(read_only=True)
    usuario_creador_detalle = serializers.SerializerMethodField()
    usuario_validador = serializers.PrimaryKeyRelatedField(read_only=True)
    usuario_validador_detalle = serializers.SerializerMethodField()

    class Meta:
        model = Alineacion
        fields = [
            "id",
            "entidad",
            "entidad_detalle",
            "objetivo_estrategico",
            "objetivo_estrategico_detalle",
            "objetivo_pnd",
            "objetivo_pnd_detalle",
            "ods",
            "ods_detalle",
            "justificacion",
            "estado",
            "usuario_creador",
            "usuario_creador_detalle",
            "usuario_validador",
            "usuario_validador_detalle",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "entidad",
            "entidad_detalle",
            "objetivo_estrategico_detalle",
            "objetivo_pnd_detalle",
            "ods_detalle",
            "estado",
            "usuario_creador",
            "usuario_creador_detalle",
            "usuario_validador",
            "usuario_validador_detalle",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_entidad_detalle(self, obj):
        return _resumen_entidad(obj.objetivo_estrategico.entidad)

    def get_objetivo_estrategico_detalle(self, obj):
        return {
            "id": obj.objetivo_estrategico_id,
            "codigo": obj.objetivo_estrategico.codigo,
            "nombre": obj.objetivo_estrategico.nombre,
            "estado": obj.objetivo_estrategico.estado,
        }

    def get_objetivo_pnd_detalle(self, obj):
        return {
            "id": obj.objetivo_pnd_id,
            "codigo": obj.objetivo_pnd.codigo,
            "nombre": obj.objetivo_pnd.nombre,
            "estado": obj.objetivo_pnd.estado,
            "eje": {
                "id": obj.objetivo_pnd.eje_id,
                "codigo": obj.objetivo_pnd.eje.codigo,
                "nombre": obj.objetivo_pnd.eje.nombre,
            },
        }

    def get_ods_detalle(self, obj):
        return {
            "id": obj.ods_id,
            "numero": obj.ods.numero,
            "nombre": obj.ods.nombre,
            "estado": obj.ods.estado,
        }

    def get_usuario_creador_detalle(self, obj):
        return _resumen_usuario(obj.usuario_creador)

    def get_usuario_validador_detalle(self, obj):
        return _resumen_usuario(obj.usuario_validador)

    def validate_justificacion(self, value):
        justificacion = value.strip()
        if not justificacion:
            raise serializers.ValidationError(
                "La justificación de la alineación es obligatoria."
            )
        return justificacion

    def validate(self, attrs):
        instance = self.instance

        if instance and instance.estado != Alineacion.EstadoAlineacion.BORRADOR:
            raise serializers.ValidationError(
                "Solo se puede editar una alineación en estado borrador."
            )

        objetivo = attrs.get(
            "objetivo_estrategico",
            getattr(instance, "objetivo_estrategico", None),
        )
        objetivo_pnd = attrs.get(
            "objetivo_pnd",
            getattr(instance, "objetivo_pnd", None),
        )
        ods = attrs.get("ods", getattr(instance, "ods", None))

        if objetivo:
            _validar_entidad_en_alcance(
                self.context.get("request"),
                objetivo.entidad_id,
            )
            if objetivo.estado != EstadoCatalogo.ACTIVO:
                raise serializers.ValidationError(
                    {
                        "objetivo_estrategico": (
                            "Solo puede alinear un objetivo estratégico activo."
                        )
                    }
                )

        if objetivo_pnd and (
            objetivo_pnd.estado != EstadoCatalogo.ACTIVO
            or objetivo_pnd.eje.estado != EstadoCatalogo.ACTIVO
        ):
            raise serializers.ValidationError(
                {"objetivo_pnd": "Solo puede alinear un objetivo PND activo."}
            )

        if ods and ods.estado != EstadoCatalogo.ACTIVO:
            raise serializers.ValidationError(
                {"ods": "Solo puede alinear un ODS activo."}
            )

        if objetivo and objetivo_pnd and ods:
            duplicados = Alineacion.objects.filter(
                objetivo_estrategico=objetivo,
                objetivo_pnd=objetivo_pnd,
                ods=ods,
            )
            if instance:
                duplicados = duplicados.exclude(pk=instance.pk)
            if duplicados.exists():
                raise serializers.ValidationError(
                    "Esta alineación institucional ya se encuentra registrada."
                )

        return attrs
