from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.configuracion.models import EntidadInstitucional
from apps.configuracion.scope import (
    obtener_alcance_usuario,
    usuario_puede_acceder_entidad,
)
from apps.objetivos.models import EstadoCatalogo, ObjetivoEstrategico
from apps.planes.models import Plan
from apps.usuarios.models import Usuario

from .models import (
    HitoProyecto,
    ProyectoInversion,
    SeguimientoProyecto,
    TipologiaIntervencion,
)
from .scope import proyecto_esta_en_alcance


ESTADOS_EDITABLES = {
    ProyectoInversion.EstadoProyecto.BORRADOR,
    ProyectoInversion.EstadoProyecto.PLANIFICADO,
}
ESTADOS_CON_SEGUIMIENTO = {
    ProyectoInversion.EstadoProyecto.EN_EJECUCION,
    ProyectoInversion.EstadoProyecto.SUSPENDIDO,
}


def validar_entidad_en_alcance(request, entidad_id):
    """Impide ampliar el alcance institucional mediante IDs del payload."""

    usuario = getattr(request, "user", None)
    if not usuario or not usuario.is_authenticated:
        raise PermissionDenied("Debe autenticarse para operar sobre una entidad.")

    if not usuario_puede_acceder_entidad(usuario, entidad_id):
        raise PermissionDenied(
            "No tiene acceso a registros de otra entidad institucional."
        )


def validar_plan_en_alcance(request, plan):
    """Evita vincular el proyecto a un plan que el actor no puede consultar."""

    usuario = getattr(request, "user", None)
    alcance = obtener_alcance_usuario(usuario)
    planes = Plan.objects.filter(pk=plan.pk, entidad_id=plan.entidad_id)
    if alcance in {"TOTAL", "GLOBAL"}:
        permitido = planes.exists()
    elif alcance in {"ENTIDAD", "PROPIO_ASIGNADO"}:
        permitido = planes.filter(
            Q(creado_por=usuario) | Q(responsable=usuario)
        ).exists()
    elif alcance in {"REVISION_ENTIDAD", "LECTURA_ENTIDAD"}:
        permitido = planes.filter(entidad_id=getattr(usuario, "entidad_id", None)).exists()
    else:
        permitido = False
    if not permitido:
        raise PermissionDenied(
            "No tiene acceso al plan seleccionado para el proyecto."
        )


def _detalle_usuario(usuario):
    if not usuario:
        return None
    nombre = usuario.get_full_name().strip()
    return {
        "id": usuario.pk,
        "username": usuario.username,
        "nombre_completo": nombre or usuario.username,
    }


class TipologiaIntervencionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipologiaIntervencion
        fields = [
            "id",
            "codigo",
            "nombre",
            "descripcion",
            "activo",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "activo",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def validate_codigo(self, value):
        codigo = value.strip().upper()
        if not codigo:
            raise serializers.ValidationError(
                "El código de la tipología es obligatorio."
            )
        existentes = TipologiaIntervencion.objects.filter(codigo__iexact=codigo)
        if self.instance:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            raise serializers.ValidationError(
                "Ya existe una tipología con este código."
            )
        return codigo

    def validate_nombre(self, value):
        nombre = value.strip()
        if not nombre:
            raise serializers.ValidationError(
                "El nombre de la tipología es obligatorio."
            )
        existentes = TipologiaIntervencion.objects.filter(nombre__iexact=nombre)
        if self.instance:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            raise serializers.ValidationError(
                "Ya existe una tipología con este nombre."
            )
        return nombre

    def validate_descripcion(self, value):
        return value.strip() if value else ""


class ProyectoInversionSerializer(serializers.ModelSerializer):
    entidad = serializers.PrimaryKeyRelatedField(
        queryset=EntidadInstitucional.objects.all()
    )
    plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.all())
    objetivo_estrategico = serializers.PrimaryKeyRelatedField(
        queryset=ObjetivoEstrategico.objects.all()
    )
    tipologia_intervencion = serializers.PrimaryKeyRelatedField(
        queryset=TipologiaIntervencion.objects.all()
    )
    responsable = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.select_related("rol").filter(is_active=True),
        required=False,
        allow_null=True,
    )
    entidad_detalle = serializers.SerializerMethodField()
    plan_detalle = serializers.SerializerMethodField()
    objetivo_estrategico_detalle = serializers.SerializerMethodField()
    tipologia_intervencion_detalle = serializers.SerializerMethodField()
    responsable_detalle = serializers.SerializerMethodField()
    creado_por_detalle = serializers.SerializerMethodField()
    hitos_count = serializers.SerializerMethodField()
    seguimientos_count = serializers.SerializerMethodField()

    class Meta:
        model = ProyectoInversion
        fields = [
            "id",
            "entidad",
            "entidad_detalle",
            "plan",
            "plan_detalle",
            "objetivo_estrategico",
            "objetivo_estrategico_detalle",
            "codigo",
            "nombre",
            "descripcion",
            "tipologia_intervencion",
            "tipologia_intervencion_detalle",
            "responsable",
            "responsable_detalle",
            "creado_por",
            "creado_por_detalle",
            "fecha_inicio",
            "fecha_fin",
            "presupuesto_estimado",
            "avance_fisico",
            "avance_financiero",
            "estado",
            "activo",
            "hitos_count",
            "seguimientos_count",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "entidad_detalle",
            "plan_detalle",
            "objetivo_estrategico_detalle",
            "tipologia_intervencion_detalle",
            "responsable_detalle",
            "creado_por",
            "creado_por_detalle",
            "avance_fisico",
            "avance_financiero",
            "estado",
            "activo",
            "hitos_count",
            "seguimientos_count",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_entidad_detalle(self, obj):
        return {
            "id": obj.entidad_id,
            "codigo_oficial": obj.entidad.codigo_oficial,
            "nombre": obj.entidad.nombre,
        }

    def get_plan_detalle(self, obj):
        return {"id": obj.plan_id, "nombre": obj.plan.nombre, "estado": obj.plan.estado}

    def get_objetivo_estrategico_detalle(self, obj):
        return {
            "id": obj.objetivo_estrategico_id,
            "codigo": obj.objetivo_estrategico.codigo,
            "nombre": obj.objetivo_estrategico.nombre,
        }

    def get_tipologia_intervencion_detalle(self, obj):
        tipologia = obj.tipologia_intervencion
        return {
            "id": tipologia.pk,
            "codigo": tipologia.codigo,
            "nombre": tipologia.nombre,
            "activo": tipologia.activo,
        }

    def get_responsable_detalle(self, obj):
        return _detalle_usuario(obj.responsable)

    def get_creado_por_detalle(self, obj):
        return _detalle_usuario(obj.creado_por)

    def get_hitos_count(self, obj):
        if hasattr(obj, "hitos_total"):
            return obj.hitos_total
        return obj.hitos.count()

    def get_seguimientos_count(self, obj):
        if hasattr(obj, "seguimientos_total"):
            return obj.seguimientos_total
        return obj.seguimientos.count()

    def validate_codigo(self, value):
        codigo = value.strip().upper()
        if not codigo:
            raise serializers.ValidationError("El código del proyecto es obligatorio.")
        return codigo

    def validate_nombre(self, value):
        nombre = value.strip()
        if not nombre:
            raise serializers.ValidationError("El nombre del proyecto es obligatorio.")
        return nombre

    def validate_descripcion(self, value):
        return value.strip() if value else ""

    def validate_tipologia_intervencion(self, value):
        if not value.activo:
            raise serializers.ValidationError(
                "La tipología de intervención seleccionada está inactiva."
            )
        return value

    def validate_responsable(self, value):
        if value and (
            not value.is_active
            or value.estado != Usuario.EstadoUsuario.ACTIVO
        ):
            raise serializers.ValidationError(
                "El responsable debe ser un usuario activo."
            )
        return value

    def validate(self, attrs):
        instance = self.instance
        if instance and instance.estado not in ESTADOS_EDITABLES:
            raise serializers.ValidationError(
                "El proyecto solo puede editarse en borrador o planificado."
            )

        entidad = attrs.get("entidad", getattr(instance, "entidad", None))
        plan = attrs.get("plan", getattr(instance, "plan", None))
        objetivo = attrs.get(
            "objetivo_estrategico",
            getattr(instance, "objetivo_estrategico", None),
        )
        responsable = attrs.get(
            "responsable",
            getattr(instance, "responsable", None),
        )
        fecha_inicio = attrs.get(
            "fecha_inicio",
            getattr(instance, "fecha_inicio", None),
        )
        fecha_fin = attrs.get("fecha_fin", getattr(instance, "fecha_fin", None))
        presupuesto = attrs.get(
            "presupuesto_estimado",
            getattr(instance, "presupuesto_estimado", None),
        )

        if entidad:
            validar_entidad_en_alcance(self.context.get("request"), entidad.pk)
            if entidad.estado != EntidadInstitucional.Estado.ACTIVA:
                raise serializers.ValidationError(
                    {"entidad": "La entidad del proyecto debe estar activa."}
                )
        if instance and entidad and entidad.pk != instance.entidad_id:
            raise serializers.ValidationError(
                {"entidad": "La entidad del proyecto no puede modificarse."}
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
        if presupuesto is not None and presupuesto < 0:
            raise serializers.ValidationError(
                {"presupuesto_estimado": "El presupuesto estimado no puede ser negativo."}
            )

        if objetivo and entidad and objetivo.entidad_id != entidad.pk:
            raise serializers.ValidationError(
                {
                    "objetivo_estrategico": (
                        "El objetivo estratégico debe pertenecer a la entidad "
                        "del proyecto."
                    )
                }
            )
        if objetivo and objetivo.estado != EstadoCatalogo.ACTIVO:
            raise serializers.ValidationError(
                {"objetivo_estrategico": "El objetivo estratégico debe estar activo."}
            )

        if plan and (not plan.activo or plan.estado == Plan.EstadoPlan.ARCHIVADO):
            raise serializers.ValidationError(
                {"plan": "El plan debe estar activo y no archivado."}
            )
        if plan:
            validar_plan_en_alcance(self.context.get("request"), plan)
        if plan and entidad and getattr(plan, "entidad_id", None) != entidad.pk:
            raise serializers.ValidationError(
                {"plan": "El plan debe pertenecer a la entidad del proyecto."}
            )

        if responsable and entidad and responsable.entidad_id != entidad.pk:
            raise serializers.ValidationError(
                {"responsable": "El responsable debe pertenecer a la entidad del proyecto."}
            )

        codigo = attrs.get("codigo", getattr(instance, "codigo", None))
        if entidad and codigo:
            duplicados = ProyectoInversion.objects.filter(
                entidad=entidad,
                codigo__iexact=codigo,
            )
            if instance:
                duplicados = duplicados.exclude(pk=instance.pk)
            if duplicados.exists():
                raise serializers.ValidationError(
                    {"codigo": "Ya existe un proyecto con este código en la entidad."}
                )

        if instance and ("fecha_inicio" in attrs or "fecha_fin" in attrs):
            hitos_fuera = instance.hitos.filter(
                Q(fecha_inicio_planificada__lt=fecha_inicio)
                | Q(fecha_fin_planificada__gt=fecha_fin)
            ).exists()
            if hitos_fuera:
                raise serializers.ValidationError(
                    "El nuevo periodo dejaría hitos fuera de las fechas del proyecto."
                )

        return attrs


class HitoProyectoSerializer(serializers.ModelSerializer):
    proyecto = serializers.PrimaryKeyRelatedField(
        queryset=ProyectoInversion.objects.all()
    )
    proyecto_detalle = serializers.SerializerMethodField()

    class Meta:
        model = HitoProyecto
        fields = [
            "id",
            "proyecto",
            "proyecto_detalle",
            "orden",
            "nombre",
            "descripcion",
            "fecha_inicio_planificada",
            "fecha_fin_planificada",
            "porcentaje_planificado",
            "activo",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "proyecto_detalle",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_proyecto_detalle(self, obj):
        return {
            "id": obj.proyecto_id,
            "codigo": obj.proyecto.codigo,
            "nombre": obj.proyecto.nombre,
            "estado": obj.proyecto.estado,
        }

    def validate_nombre(self, value):
        nombre = value.strip()
        if not nombre:
            raise serializers.ValidationError("El nombre del hito es obligatorio.")
        return nombre

    def validate_descripcion(self, value):
        return value.strip() if value else ""

    def validate(self, attrs):
        instance = self.instance
        proyecto = attrs.get("proyecto", getattr(instance, "proyecto", None))
        if not proyecto:
            return attrs

        validar_entidad_en_alcance(
            self.context.get("request"),
            proyecto.entidad_id,
        )
        if not proyecto_esta_en_alcance(
            proyecto,
            getattr(self.context.get("request"), "user", None),
        ):
            raise PermissionDenied("No tiene acceso al proyecto seleccionado.")
        if instance and proyecto.pk != instance.proyecto_id:
            raise serializers.ValidationError(
                {"proyecto": "El proyecto de un hito no puede modificarse."}
            )
        if proyecto.estado not in ESTADOS_EDITABLES:
            raise serializers.ValidationError(
                "El cronograma solo puede editarse en borrador o planificado."
            )

        fecha_inicio = attrs.get(
            "fecha_inicio_planificada",
            getattr(instance, "fecha_inicio_planificada", None),
        )
        fecha_fin = attrs.get(
            "fecha_fin_planificada",
            getattr(instance, "fecha_fin_planificada", None),
        )
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError(
                {
                    "fecha_fin_planificada": (
                        "La fecha final del hito no puede ser anterior a la fecha inicial."
                    )
                }
            )
        if fecha_inicio and fecha_inicio < proyecto.fecha_inicio:
            raise serializers.ValidationError(
                {"fecha_inicio_planificada": "El hito no puede iniciar antes que el proyecto."}
            )
        if fecha_fin and fecha_fin > proyecto.fecha_fin:
            raise serializers.ValidationError(
                {"fecha_fin_planificada": "El hito no puede finalizar después que el proyecto."}
            )

        orden = attrs.get("orden", getattr(instance, "orden", None))
        nombre = attrs.get("nombre", getattr(instance, "nombre", None))
        por_orden = HitoProyecto.objects.filter(proyecto=proyecto, orden=orden)
        por_nombre = HitoProyecto.objects.filter(
            proyecto=proyecto,
            nombre__iexact=nombre,
        )
        if instance:
            por_orden = por_orden.exclude(pk=instance.pk)
            por_nombre = por_nombre.exclude(pk=instance.pk)
        errores = {}
        if por_orden.exists():
            errores["orden"] = "Ya existe un hito con este orden en el proyecto."
        if por_nombre.exists():
            errores["nombre"] = "Ya existe un hito con este nombre en el proyecto."

        porcentaje = attrs.get(
            "porcentaje_planificado",
            getattr(instance, "porcentaje_planificado", Decimal("0")),
        )
        otros = HitoProyecto.objects.filter(proyecto=proyecto)
        if instance:
            otros = otros.exclude(pk=instance.pk)
        acumulado = otros.aggregate(total=Sum("porcentaje_planificado"))["total"] or Decimal("0")
        if acumulado + porcentaje > Decimal("100"):
            errores["porcentaje_planificado"] = (
                "La suma de porcentajes planificados de los hitos no puede superar el 100%."
            )
        if errores:
            raise serializers.ValidationError(errores)
        return attrs


class SeguimientoProyectoSerializer(serializers.ModelSerializer):
    proyecto = serializers.PrimaryKeyRelatedField(read_only=True)
    registrado_por = serializers.PrimaryKeyRelatedField(read_only=True)
    proyecto_detalle = serializers.SerializerMethodField()
    hito_detalle = serializers.SerializerMethodField()
    registrado_por_detalle = serializers.SerializerMethodField()

    class Meta:
        model = SeguimientoProyecto
        fields = [
            "id",
            "proyecto",
            "proyecto_detalle",
            "hito",
            "hito_detalle",
            "fecha_registro",
            "avance_fisico",
            "avance_financiero",
            "observacion",
            "registrado_por",
            "registrado_por_detalle",
            "fecha_creacion",
        ]
        read_only_fields = [
            "id",
            "proyecto",
            "proyecto_detalle",
            "hito_detalle",
            "registrado_por",
            "registrado_por_detalle",
            "fecha_creacion",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        proyecto = self.context.get("proyecto")
        if proyecto is not None:
            self.fields["hito"].queryset = proyecto.hitos.filter(activo=True)

    def get_proyecto_detalle(self, obj):
        return {
            "id": obj.proyecto_id,
            "codigo": obj.proyecto.codigo,
            "nombre": obj.proyecto.nombre,
        }

    def get_hito_detalle(self, obj):
        if not obj.hito:
            return None
        return {"id": obj.hito_id, "orden": obj.hito.orden, "nombre": obj.hito.nombre}

    def get_registrado_por_detalle(self, obj):
        return _detalle_usuario(obj.registrado_por)

    def validate_observacion(self, value):
        return value.strip() if value else ""

    def validate(self, attrs):
        proyecto = self.context.get("proyecto")
        if proyecto is None:
            raise serializers.ValidationError(
                "El seguimiento debe registrarse desde la acción del proyecto."
            )

        validar_entidad_en_alcance(
            self.context.get("request"),
            proyecto.entidad_id,
        )
        if proyecto.estado not in ESTADOS_CON_SEGUIMIENTO:
            raise serializers.ValidationError(
                "Solo se registra seguimiento para proyectos en ejecución o suspendidos."
            )

        hito = attrs.get("hito")
        if hito and hito.proyecto_id != proyecto.pk:
            raise serializers.ValidationError(
                {"hito": "El hito debe pertenecer al proyecto del seguimiento."}
            )
        if hito and not hito.activo:
            raise serializers.ValidationError(
                {"hito": "No se puede registrar seguimiento sobre un hito inactivo."}
            )

        fecha = attrs.get("fecha_registro", timezone.localdate())
        if not proyecto.fecha_inicio <= fecha <= proyecto.fecha_fin:
            raise serializers.ValidationError(
                {
                    "fecha_registro": (
                        "La fecha del seguimiento debe estar dentro del periodo "
                        "del proyecto."
                    )
                }
            )
        if fecha > timezone.localdate():
            raise serializers.ValidationError(
                {"fecha_registro": "No se puede registrar un seguimiento futuro."}
            )
        if SeguimientoProyecto.objects.filter(
            proyecto=proyecto,
            fecha_registro=fecha,
        ).exists():
            raise serializers.ValidationError(
                {
                    "fecha_registro": (
                        "Ya existe un seguimiento para este proyecto en la fecha indicada."
                    )
                }
            )
        return attrs


class DevolucionProyectoSerializer(serializers.Serializer):
    observacion = serializers.CharField(
        max_length=2000,
        trim_whitespace=True,
        allow_blank=False,
    )

    def validate_observacion(self, value):
        observacion = value.strip()
        if not observacion:
            raise serializers.ValidationError(
                "La observación de devolución es obligatoria."
            )
        return observacion
