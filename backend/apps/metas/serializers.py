from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone

from apps.configuracion.scope import (
    obtener_alcance_usuario,
    usuario_puede_acceder_entidad,
)
from apps.objetivos.models import EstadoCatalogo, ObjetivoEstrategico
from apps.planes.models import Plan

from .models import AvanceIndicador, Indicador, Meta
from .services import calcular_seguimiento_indicador, calcular_seguimiento_meta


def _validar_alcance_plan(serializer, plan):
    request = serializer.context.get("request")
    usuario = getattr(request, "user", None)
    if not usuario_puede_acceder_entidad(usuario, plan.entidad_id):
        raise PermissionDenied(
            "No puede relacionar registros con un plan de otra entidad."
        )
    if obtener_alcance_usuario(usuario) in {"ENTIDAD", "PROPIO_ASIGNADO"} and (
        plan.creado_por_id != getattr(usuario, "pk", None)
        and plan.responsable_id != getattr(usuario, "pk", None)
    ):
        raise PermissionDenied(
            "Solo puede relacionar registros con planes propios o asignados."
        )


class MetaSerializer(serializers.ModelSerializer):
    """
    Serializador para metas institucionales.

    Permite asociar una meta a un plan y expone una representación resumida del
    plan para facilitar su consumo desde la interfaz.
    """

    plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.all())
    objetivo_estrategico = serializers.PrimaryKeyRelatedField(
        queryset=ObjetivoEstrategico.objects.all(),
        required=True,
        allow_null=False,
        error_messages={
            "required": "Debe seleccionar el objetivo estratégico de la meta.",
            "null": "Debe seleccionar el objetivo estratégico de la meta.",
            "does_not_exist": "El objetivo estratégico seleccionado no existe.",
            "incorrect_type": "El objetivo estratégico seleccionado no es válido.",
        },
    )
    plan_detalle = serializers.SerializerMethodField()
    objetivo_estrategico_detalle = serializers.SerializerMethodField()
    indicadores_count = serializers.SerializerMethodField()
    progreso = serializers.SerializerMethodField()
    estado_seguimiento = serializers.SerializerMethodField()
    etiqueta_estado_seguimiento = serializers.SerializerMethodField()
    proxima_medicion = serializers.SerializerMethodField()

    class Meta:
        model = Meta
        fields = [
            "id",
            "plan",
            "plan_detalle",
            "objetivo_estrategico",
            "objetivo_estrategico_detalle",
            "nombre",
            "descripcion",
            "resultado_esperado",
            "fecha_inicio",
            "fecha_fin",
            "estado",
            "activa",
            "indicadores_count",
            "progreso",
            "estado_seguimiento",
            "etiqueta_estado_seguimiento",
            "proxima_medicion",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "plan_detalle",
            "objetivo_estrategico_detalle",
            "estado",
            "activa",
            "indicadores_count",
            "progreso",
            "estado_seguimiento",
            "etiqueta_estado_seguimiento",
            "proxima_medicion",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_plan_detalle(self, obj):
        """Devuelve información básica del plan asociado."""

        return {
            "id": obj.plan.id,
            "nombre": obj.plan.nombre,
            "estado": obj.plan.estado,
            "entidad": {
                "id": obj.plan.entidad_id,
                "codigo_oficial": obj.plan.entidad.codigo_oficial,
                "nombre": obj.plan.entidad.nombre,
            },
        }

    def get_objetivo_estrategico_detalle(self, obj):
        if obj.objetivo_estrategico_id is None:
            return None
        objetivo = obj.objetivo_estrategico
        return {
            "id": objetivo.pk,
            "codigo": objetivo.codigo,
            "nombre": objetivo.nombre,
            "estado": objetivo.estado,
            "entidad": {
                "id": objetivo.entidad_id,
                "codigo_oficial": objetivo.entidad.codigo_oficial,
                "nombre": objetivo.entidad.nombre,
            },
            "alineaciones": [
                {
                    "id": alineacion.pk,
                    "estado": alineacion.estado,
                    "objetivo_pnd": {
                        "id": alineacion.objetivo_pnd_id,
                        "codigo": alineacion.objetivo_pnd.codigo,
                        "nombre": alineacion.objetivo_pnd.nombre,
                    },
                    "ods": {
                        "id": alineacion.ods_id,
                        "numero": alineacion.ods.numero,
                        "nombre": alineacion.ods.nombre,
                    },
                }
                for alineacion in objetivo.alineaciones.all()
            ],
        }

    def get_indicadores_count(self, obj):
        """Devuelve el número de indicadores asociados a la meta."""

        if hasattr(obj, "indicadores_count_anotado"):
            return obj.indicadores_count_anotado
        return obj.indicadores.count()

    def _seguimiento(self, obj):
        cache = getattr(obj, "_seguimiento_serializer", None)
        if cache is None:
            cache = calcular_seguimiento_meta(obj)
            obj._seguimiento_serializer = cache
        return cache

    def get_progreso(self, obj):
        return float(self._seguimiento(obj)["progreso"])

    def get_estado_seguimiento(self, obj):
        return self._seguimiento(obj)["estado_seguimiento"]

    def get_etiqueta_estado_seguimiento(self, obj):
        return self._seguimiento(obj)["etiqueta_estado_seguimiento"]

    def get_proxima_medicion(self, obj):
        return self._seguimiento(obj)["proxima_medicion"]

    def validate_nombre(self, value):
        """Normaliza y valida el nombre de la meta."""

        nombre = value.strip()

        if not nombre:
            raise serializers.ValidationError("El nombre de la meta es obligatorio.")

        if len(nombre) < 3:
            raise serializers.ValidationError(
                "El nombre de la meta debe tener al menos 3 caracteres."
            )

        return nombre

    def validate_descripcion(self, value):
        """Normaliza la descripción de la meta."""

        return value.strip() if value else ""

    def validate_resultado_esperado(self, value):
        """Normaliza el resultado esperado de la meta."""

        return value.strip() if value else ""

    def validate_plan(self, value):
        """Evita asociar metas a planes inactivos o archivados."""

        if not value.activo or value.estado == Plan.EstadoPlan.ARCHIVADO:
            raise serializers.ValidationError(
                "No se puede registrar una meta en un plan inactivo o archivado."
            )
        if value.estado not in {
            Plan.EstadoPlan.BORRADOR,
            Plan.EstadoPlan.DEVUELTO,
            Plan.EstadoPlan.RECHAZADO,
        }:
            raise serializers.ValidationError(
                "Solo se pueden gestionar metas en un plan editable."
            )

        if (
            self.instance
            and value.pk != self.instance.plan_id
            and self.instance.indicadores.exists()
        ):
            raise serializers.ValidationError(
                "No se puede cambiar el plan de una meta con indicadores."
            )

        _validar_alcance_plan(self, value)
        return value

    def validate_objetivo_estrategico(self, value):
        conserva_objetivo_existente = (
            self.instance is not None
            and value.pk == self.instance.objetivo_estrategico_id
        )
        if value.estado != EstadoCatalogo.ACTIVO and not conserva_objetivo_existente:
            raise serializers.ValidationError(
                "Solo puede utilizar un objetivo estratégico activo."
            )

        request = self.context.get("request")
        usuario = getattr(request, "user", None)
        if not usuario_puede_acceder_entidad(usuario, value.entidad_id):
            raise PermissionDenied(
                "No puede relacionar la meta con un objetivo de otra entidad."
            )

        if (
            self.instance
            and self.instance.objetivo_estrategico_id is not None
            and value.pk != self.instance.objetivo_estrategico_id
            and self.instance.indicadores.exists()
        ):
            raise serializers.ValidationError(
                "No se puede cambiar el objetivo de una meta con indicadores."
            )
        return value

    def validate(self, attrs):
        """Valida la coherencia del rango de fechas de la meta."""

        fecha_inicio = attrs.get("fecha_inicio", getattr(self.instance, "fecha_inicio", None))
        fecha_fin = attrs.get("fecha_fin", getattr(self.instance, "fecha_fin", None))
        plan = attrs.get("plan", getattr(self.instance, "plan", None))
        objetivo = attrs.get(
            "objetivo_estrategico",
            getattr(self.instance, "objetivo_estrategico", None),
        )

        if objetivo is None:
            raise serializers.ValidationError(
                {
                    "objetivo_estrategico": (
                        "Debe seleccionar el objetivo estratégico de la meta."
                    )
                }
            )

        if plan and objetivo and plan.entidad_id != objetivo.entidad_id:
            raise serializers.ValidationError(
                {
                    "objetivo_estrategico": (
                        "El objetivo estratégico debe pertenecer a la entidad del plan."
                    )
                }
            )

        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError(
                {
                    "fecha_fin": (
                        "La fecha de finalización no puede ser anterior "
                        "a la fecha de inicio."
                    )
                }
            )

        if plan and fecha_inicio and fecha_inicio < plan.periodo_inicio:
            raise serializers.ValidationError(
                {
                    "fecha_inicio": (
                        "La meta no puede iniciar antes del periodo del plan."
                    )
                }
            )
        if plan and fecha_fin and fecha_fin > plan.periodo_fin:
            raise serializers.ValidationError(
                {
                    "fecha_fin": (
                        "La meta no puede finalizar después del periodo del plan."
                    )
                }
            )

        return attrs


class IndicadorSerializer(serializers.ModelSerializer):
    """
    Serializador para indicadores de cumplimiento.

    El indicador queda asociado a una meta y conserva valores base, meta y
    actual para seguimiento periódico.
    """

    meta = serializers.PrimaryKeyRelatedField(queryset=Meta.objects.all())
    meta_detalle = serializers.SerializerMethodField()
    avances_count = serializers.SerializerMethodField()
    progreso = serializers.SerializerMethodField()
    avance_esperado = serializers.SerializerMethodField()
    estado_seguimiento = serializers.SerializerMethodField()
    etiqueta_estado_seguimiento = serializers.SerializerMethodField()
    proxima_medicion = serializers.SerializerMethodField()
    ultimo_avance = serializers.SerializerMethodField()
    tendencia = serializers.SerializerMethodField()

    class Meta:
        model = Indicador
        fields = [
            "id",
            "meta",
            "meta_detalle",
            "nombre",
            "descripcion",
            "unidad_medida",
            "valor_base",
            "valor_meta",
            "valor_actual",
            "frecuencia",
            "sentido",
            "ponderacion",
            "activo",
            "validado",
            "validado_por",
            "fecha_validacion",
            "avances_count",
            "progreso",
            "avance_esperado",
            "estado_seguimiento",
            "etiqueta_estado_seguimiento",
            "proxima_medicion",
            "ultimo_avance",
            "tendencia",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "meta_detalle",
            "valor_actual",
            "activo",
            "validado",
            "validado_por",
            "fecha_validacion",
            "avances_count",
            "progreso",
            "avance_esperado",
            "estado_seguimiento",
            "etiqueta_estado_seguimiento",
            "proxima_medicion",
            "ultimo_avance",
            "tendencia",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_meta_detalle(self, obj):
        """Devuelve información básica de la meta asociada."""

        return {
            "id": obj.meta.id,
            "nombre": obj.meta.nombre,
            "plan": obj.meta.plan.nombre,
            "plan_id": obj.meta.plan_id,
            "plan_estado": obj.meta.plan.estado,
            "entidad": {
                "id": obj.meta.plan.entidad_id,
                "codigo_oficial": obj.meta.plan.entidad.codigo_oficial,
                "nombre": obj.meta.plan.entidad.nombre,
            },
            "objetivo_estrategico": {
                "id": obj.meta.objetivo_estrategico_id,
                "codigo": obj.meta.objetivo_estrategico.codigo,
                "nombre": obj.meta.objetivo_estrategico.nombre,
            },
            "alineaciones": [
                {
                    "id": alineacion.pk,
                    "estado": alineacion.estado,
                    "objetivo_pnd": {
                        "id": alineacion.objetivo_pnd_id,
                        "codigo": alineacion.objetivo_pnd.codigo,
                        "nombre": alineacion.objetivo_pnd.nombre,
                    },
                    "ods": {
                        "id": alineacion.ods_id,
                        "numero": alineacion.ods.numero,
                        "nombre": alineacion.ods.nombre,
                    },
                }
                for alineacion in (
                    obj.meta.objetivo_estrategico.alineaciones.all()
                )
            ],
        }

    def get_avances_count(self, obj):
        """Devuelve el número de avances registrados para el indicador."""

        return obj.avances.count()

    def _seguimiento(self, obj):
        cache = getattr(obj, "_seguimiento_serializer", None)
        if cache is None:
            cache = calcular_seguimiento_indicador(obj)
            obj._seguimiento_serializer = cache
        return cache

    def get_progreso(self, obj):
        return float(self._seguimiento(obj)["progreso"])

    def get_avance_esperado(self, obj):
        return float(self._seguimiento(obj)["avance_esperado"])

    def get_estado_seguimiento(self, obj):
        return self._seguimiento(obj)["estado_seguimiento"]

    def get_etiqueta_estado_seguimiento(self, obj):
        return self._seguimiento(obj)["etiqueta_estado_seguimiento"]

    def get_proxima_medicion(self, obj):
        return self._seguimiento(obj)["proxima_medicion"]

    def get_ultimo_avance(self, obj):
        return self._seguimiento(obj)["ultimo_avance"]

    def get_tendencia(self, obj):
        return self._seguimiento(obj)["tendencia"]

    def validate_nombre(self, value):
        """Normaliza y valida el nombre del indicador."""

        nombre = value.strip()

        if not nombre:
            raise serializers.ValidationError(
                "El nombre del indicador es obligatorio."
            )

        if len(nombre) < 3:
            raise serializers.ValidationError(
                "El nombre del indicador debe tener al menos 3 caracteres."
            )

        return nombre

    def validate_descripcion(self, value):
        """Normaliza la descripción del indicador."""

        return value.strip() if value else ""

    def validate_unidad_medida(self, value):
        """Valida la unidad de medida del indicador."""

        unidad = value.strip()

        if not unidad:
            raise serializers.ValidationError("La unidad de medida es obligatoria.")

        return unidad

    def validate_meta(self, value):
        """Evita crear indicadores sobre metas archivadas o inactivas."""

        if not value.activa or value.estado != Meta.EstadoMeta.ACTIVA:
            raise serializers.ValidationError(
                "No se puede registrar un indicador en una meta que no esté activa."
            )
        if value.plan.estado not in {
            Plan.EstadoPlan.BORRADOR,
            Plan.EstadoPlan.DEVUELTO,
            Plan.EstadoPlan.RECHAZADO,
        }:
            raise serializers.ValidationError(
                "No se puede cambiar un indicador dentro de un plan no editable."
            )
        if (
            self.instance
            and value.pk != self.instance.meta_id
            and self.instance.avances.exists()
        ):
            raise serializers.ValidationError(
                "No se puede cambiar la meta de un indicador con avances."
            )

        _validar_alcance_plan(self, value.plan)
        return value

    def validate_valor_base(self, value):
        """Valida que el valor base no sea negativo."""

        if value < 0:
            raise serializers.ValidationError("El valor base no puede ser negativo.")

        return value

    def validate_valor_meta(self, value):
        """Valida que el valor meta no sea negativo."""

        if value < 0:
            raise serializers.ValidationError("El valor meta no puede ser negativo.")

        return value

    def validate(self, attrs):
        base = attrs.get(
            "valor_base",
            getattr(self.instance, "valor_base", None),
        )
        meta = attrs.get(
            "valor_meta",
            getattr(self.instance, "valor_meta", None),
        )
        sentido = attrs.get(
            "sentido",
            getattr(
                self.instance,
                "sentido",
                Indicador.SentidoMedicion.ASCENDENTE,
            ),
        )

        if base is not None and meta is not None:
            if (
                sentido == Indicador.SentidoMedicion.ASCENDENTE
                and meta <= base
            ):
                raise serializers.ValidationError(
                    {
                        "valor_meta": (
                            "En un indicador ascendente, el valor meta debe "
                            "ser mayor que el valor base."
                        )
                    }
                )
            if (
                sentido == Indicador.SentidoMedicion.DESCENDENTE
                and meta >= base
            ):
                raise serializers.ValidationError(
                    {
                        "valor_meta": (
                            "En un indicador descendente, el valor meta debe "
                            "ser menor que el valor base."
                        )
                    }
                )

        return attrs


class AvanceIndicadorSerializer(serializers.ModelSerializer):
    """
    Serializador para avances de indicadores.

    Cada avance registra un valor medido en una fecha concreta y puede incluir
    una observación para trazabilidad.
    """

    indicador = serializers.PrimaryKeyRelatedField(queryset=Indicador.objects.all())
    indicador_detalle = serializers.SerializerMethodField()
    registrado_por = serializers.PrimaryKeyRelatedField(read_only=True)
    registrado_por_detalle = serializers.SerializerMethodField()

    class Meta:
        model = AvanceIndicador
        fields = [
            "id",
            "indicador",
            "indicador_detalle",
            "fecha_registro",
            "valor",
            "observacion",
            "evidencia",
            "registrado_por",
            "registrado_por_detalle",
            "fecha_creacion",
        ]
        read_only_fields = [
            "id",
            "indicador_detalle",
            "registrado_por",
            "registrado_por_detalle",
            "fecha_creacion",
        ]

    def get_indicador_detalle(self, obj):
        """Devuelve información básica del indicador asociado."""

        return {
            "id": obj.indicador.id,
            "nombre": obj.indicador.nombre,
            "meta": obj.indicador.meta.nombre,
            "unidad_medida": obj.indicador.unidad_medida,
        }

    def get_registrado_por_detalle(self, obj):
        """Devuelve información básica del usuario que registró el avance."""

        if not obj.registrado_por:
            return None

        nombre_completo = (
            f"{obj.registrado_por.first_name} {obj.registrado_por.last_name}"
        ).strip()

        return {
            "id": obj.registrado_por.id,
            "username": obj.registrado_por.username,
            "nombre_completo": nombre_completo or obj.registrado_por.username,
        }

    def validate_indicador(self, value):
        """Evita registrar avances sobre indicadores inactivos."""

        if not value.activo:
            raise serializers.ValidationError(
                "No se puede registrar avance sobre un indicador inactivo."
            )
        if not value.validado:
            raise serializers.ValidationError(
                "El indicador debe estar validado antes de registrar avances."
            )
        if (
            not value.meta.activa
            or value.meta.estado != Meta.EstadoMeta.ACTIVA
        ):
            raise serializers.ValidationError(
                "La meta del indicador debe estar activa."
            )
        if value.meta.plan.estado != Plan.EstadoPlan.APROBADO:
            raise serializers.ValidationError(
                "Solo se registran avances de indicadores de planes aprobados."
            )

        _validar_alcance_plan(self, value.meta.plan)
        return value

    def validate_observacion(self, value):
        """Normaliza la observación del avance."""

        return value.strip() if value else ""

    def validate_evidencia(self, value):
        return value.strip() if value else ""

    def validate_fecha_registro(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError(
                "La fecha del avance no puede estar en el futuro."
            )
        return value

    def validate_valor(self, value):
        """Valida que el valor registrado no sea negativo."""

        if value < 0:
            raise serializers.ValidationError("El valor del avance no puede ser negativo.")

        return value

    def validate(self, attrs):
        indicador = attrs.get(
            "indicador",
            getattr(self.instance, "indicador", None),
        )
        fecha = attrs.get(
            "fecha_registro",
            getattr(self.instance, "fecha_registro", None),
        )
        if indicador and fecha:
            meta = indicador.meta
            if fecha < meta.fecha_inicio or fecha > meta.fecha_fin:
                raise serializers.ValidationError(
                    {
                        "fecha_registro": (
                            "La fecha del avance debe estar dentro del periodo "
                            "de la meta."
                        )
                    }
                )
            duplicados = AvanceIndicador.objects.filter(
                indicador=indicador,
                fecha_registro=fecha,
            )
            if self.instance:
                duplicados = duplicados.exclude(pk=self.instance.pk)
            if duplicados.exists():
                raise serializers.ValidationError(
                    {
                        "fecha_registro": (
                            "Ya existe un avance de este indicador para la "
                            "fecha seleccionada."
                        )
                    }
                )
        return attrs
