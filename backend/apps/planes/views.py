from django.db import transaction
from django.db.models import Prefetch, Q
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.auditoria.services import (
    AuditoriaModelViewSetMixin,
    registrar_evento,
    serializar_instancia,
)
from apps.configuracion.scope import (
    obtener_alcance_usuario,
)
from apps.configuracion.models import EntidadInstitucional
from apps.metas.models import AvanceIndicador, Indicador, Meta
from apps.metas.serializers import (
    AvanceIndicadorSerializer,
    IndicadorSerializer,
    MetaSerializer,
)
from apps.metas.services import (
    calcular_seguimiento_indicador,
    calcular_seguimiento_meta,
    calcular_seguimiento_objetivo,
    calcular_seguimiento_plan,
)
from apps.objetivos.models import Alineacion
from apps.objetivos.serializers import AlineacionSerializer
from apps.roles.permissions import HasSipeipPermission

from .models import HistorialEstadoPlan, Plan
from .scope import filtrar_queryset_por_alcance_plan
from .services import (
    agrupar_metas_por_objetivo,
    evaluar_integridad_plan,
)
from .serializers import (
    HistorialEstadoPlanSerializer,
    PlanSerializer,
    TransicionPlanSerializer,
)


class PlanViewSet(AuditoriaModelViewSetMixin, viewsets.ModelViewSet):
    queryset = (
        Plan.objects.select_related(
            "entidad",
            "responsable",
            "creado_por",
            "revisor",
            "aprobado_por",
        )
        .prefetch_related(
            Prefetch(
                "historial_estados",
                queryset=HistorialEstadoPlan.objects.select_related("usuario"),
            ),
            Prefetch(
                "metas",
                queryset=Meta.objects.select_related(
                    "plan__entidad",
                    "objetivo_estrategico__entidad",
                ).prefetch_related(
                    Prefetch(
                        "objetivo_estrategico__alineaciones",
                        queryset=Alineacion.objects.select_related(
                            "objetivo_pnd__eje",
                            "ods",
                            "usuario_creador",
                            "usuario_validador",
                        ),
                    ),
                    Prefetch(
                        "indicadores",
                        queryset=Indicador.objects.select_related(
                            "validado_por",
                        ).prefetch_related(
                            Prefetch(
                                "avances",
                                queryset=AvanceIndicador.objects.select_related(
                                    "registrado_por"
                                ),
                            )
                        ),
                    ),
                ),
            ),
        )
        .all()
    )
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "planes.ver",
        "retrieve": "planes.ver",
        "create": "planes.crear",
        "update": "planes.editar",
        "partial_update": "planes.editar",
        "destroy": "planes.eliminar",
        "enviar_a_revision": "planes.enviar_revision",
        "revisar": "planes.revisar",
        "devolver": "planes.devolver",
        "aprobar": "planes.aprobar",
        "rechazar": "planes.rechazar",
        "archivar": "planes.archivar",
        "historial": "planes.ver",
        "expediente": "planes.ver",
        "seguimiento": "planes.ver",
        "validacion": "planes.ver",
    }
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "nombre",
        "descripcion",
        "estado",
        "entidad__nombre",
        "responsable__username",
        "responsable__first_name",
        "responsable__last_name",
    ]
    ordering_fields = [
        "id",
        "nombre",
        "estado",
        "periodo_inicio",
        "periodo_fin",
        "fecha_creacion",
    ]
    ordering = ["-fecha_creacion"]
    audit_modulo = "planes"
    audit_funcionalidad = "planes institucionales"

    def get_queryset(self):
        queryset = filtrar_queryset_por_alcance_plan(
            super().get_queryset(),
            self.request.user,
        )
        if obtener_alcance_usuario(self.request.user) in {
            "ENTIDAD",
            "PROPIO_ASIGNADO",
        }:
            queryset = queryset.filter(
                Q(creado_por=self.request.user) | Q(responsable=self.request.user)
            )
        return queryset.distinct()

    def perform_create(self, serializer):
        usuario = self.request.user
        alcance = obtener_alcance_usuario(usuario)
        entidad = serializer.validated_data.get("entidad") or getattr(
            usuario, "entidad", None
        )
        if entidad is None:
            raise serializers.ValidationError(
                {"entidad": "Debe asignar una entidad institucional al plan."}
            )
        if entidad.estado != EntidadInstitucional.Estado.ACTIVA:
            raise serializers.ValidationError(
                {"entidad": "No se pueden registrar planes en una entidad inactiva."}
            )
        if Plan.objects.filter(
            entidad=entidad,
            nombre__iexact=serializer.validated_data.get("nombre", ""),
        ).exists():
            raise serializers.ValidationError(
                {"nombre": "Ya existe un plan con este nombre en la entidad."}
            )
        extras = {"entidad": entidad, "creado_por": usuario}
        if alcance in {"ENTIDAD", "PROPIO_ASIGNADO"} and not serializer.validated_data.get(
            "responsable"
        ):
            extras["responsable"] = usuario
        with transaction.atomic():
            plan = serializer.save(**extras)
            registrar_evento(
                request=self.request,
                modulo=self.audit_modulo,
                funcionalidad=self.audit_funcionalidad,
                accion="CREAR",
                instancia=plan,
            )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        plan_autorizado = self.get_object()
        plan = self._obtener_instancia_bloqueada(plan_autorizado)
        if plan.estado not in {
            Plan.EstadoPlan.BORRADOR,
            Plan.EstadoPlan.DEVUELTO,
            Plan.EstadoPlan.RECHAZADO,
        }:
            return Response(
                {"detail": "El plan no puede editarse en su estado actual."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        plan_autorizado = self.get_object()
        plan = self._obtener_instancia_bloqueada(plan_autorizado)
        if plan.estado in {
            Plan.EstadoPlan.EN_REVISION,
            Plan.EstadoPlan.EN_REVISION_INICIADA,
            Plan.EstadoPlan.APROBADO,
        }:
            return Response(
                {
                    "detail": (
                        "No se puede eliminar un plan revisado o aprobado. "
                        "Use una acción de archivo autorizada."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {
                    "detail": (
                        "No se puede eliminar este plan porque conserva metas, "
                        "proyectos o historial protegido."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

    def _leer_observacion(self, request, requerida=False):
        entrada = TransicionPlanSerializer(
            data=request.data,
            context={"observacion_requerida": requerida},
        )
        entrada.is_valid(raise_exception=True)
        return entrada.validated_data.get("observacion", "")

    def _transicionar(
        self,
        *,
        estados_origen,
        estado_nuevo,
        accion,
        observacion="",
        activo=None,
        validacion_requerida=None,
        registrar_envio=False,
        asignar_revisor=False,
        requiere_revisor_actual=False,
        limpiar_revision=False,
        registrar_aprobacion=False,
    ):
        plan_autorizado = self.get_object()
        with transaction.atomic():
            plan = self._obtener_instancia_bloqueada(plan_autorizado)
            if plan.estado not in estados_origen:
                return Response(
                    {
                        "detail": (
                            f"La acción '{accion.lower()}' no está permitida "
                            f"desde el estado {plan.estado}."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            if requiere_revisor_actual and not (
                self.request.user.is_superuser
                and self.request.user.is_active
            ):
                if plan.revisor_id != self.request.user.pk:
                    return Response(
                        {
                            "code": "revision_asignada",
                            "detail": (
                                "Solo el supervisor que inició esta revisión "
                                "puede resolverla."
                            ),
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

            if validacion_requerida:
                evaluacion = evaluar_integridad_plan(plan)
                clave = (
                    "listo_para_aprobacion"
                    if validacion_requerida == "aprobacion"
                    else "listo_para_revision"
                )
                if not evaluacion[clave]:
                    return Response(
                        {
                            "code": "plan_incompleto",
                            "detail": (
                                "El plan no cumple las condiciones necesarias "
                                "para completar esta acción."
                            ),
                            "validacion": evaluacion,
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

            estado_anterior = plan.estado
            antes = serializar_instancia(plan)
            plan.estado = estado_nuevo
            campos = ["estado", "fecha_actualizacion"]

            ahora = timezone.now()
            if registrar_envio:
                plan.fecha_envio_revision = ahora
                plan.revisor = None
                plan.fecha_inicio_revision = None
                plan.aprobado_por = None
                plan.fecha_aprobacion = None
                campos.extend(
                    [
                        "fecha_envio_revision",
                        "revisor",
                        "fecha_inicio_revision",
                        "aprobado_por",
                        "fecha_aprobacion",
                    ]
                )
            if asignar_revisor:
                plan.revisor = self.request.user
                plan.fecha_inicio_revision = ahora
                campos.extend(["revisor", "fecha_inicio_revision"])
            if limpiar_revision:
                plan.revisor = None
                plan.fecha_inicio_revision = None
                plan.aprobado_por = None
                plan.fecha_aprobacion = None
                campos.extend(
                    [
                        "revisor",
                        "fecha_inicio_revision",
                        "aprobado_por",
                        "fecha_aprobacion",
                    ]
                )
            if registrar_aprobacion:
                plan.aprobado_por = self.request.user
                plan.fecha_aprobacion = ahora
                campos.extend(["aprobado_por", "fecha_aprobacion"])
            if activo is not None:
                plan.activo = activo
                campos.append("activo")
            plan.save(update_fields=list(dict.fromkeys(campos)))
            HistorialEstadoPlan.objects.create(
                plan=plan,
                usuario=self.request.user,
                accion=accion,
                estado_anterior=estado_anterior,
                estado_nuevo=estado_nuevo,
                observacion=observacion,
            )
            registrar_evento(
                request=self.request,
                modulo=self.audit_modulo,
                funcionalidad=self.audit_funcionalidad,
                accion=accion,
                instancia=plan,
                antes=antes,
                detalle=observacion,
            )
        plan = self.get_queryset().get(pk=plan.pk)
        return Response(self.get_serializer(plan).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="enviar-a-revision")
    def enviar_a_revision(self, request, pk=None):
        return self._transicionar(
            estados_origen={
                Plan.EstadoPlan.BORRADOR,
                Plan.EstadoPlan.DEVUELTO,
                Plan.EstadoPlan.RECHAZADO,
            },
            estado_nuevo=Plan.EstadoPlan.EN_REVISION,
            accion="ENVIAR_REVISION",
            observacion=self._leer_observacion(request),
            validacion_requerida="revision",
            registrar_envio=True,
        )

    @action(detail=True, methods=["post"])
    def revisar(self, request, pk=None):
        return self._transicionar(
            estados_origen={Plan.EstadoPlan.EN_REVISION},
            estado_nuevo=Plan.EstadoPlan.EN_REVISION_INICIADA,
            accion="INICIAR_REVISION",
            observacion=self._leer_observacion(request),
            asignar_revisor=True,
        )

    @action(detail=True, methods=["post"])
    def devolver(self, request, pk=None):
        return self._resolver_revision(
            request,
            Plan.EstadoPlan.DEVUELTO,
            "DEVOLVER",
            observacion_requerida=True,
        )

    @action(detail=True, methods=["post"])
    def aprobar(self, request, pk=None):
        return self._resolver_revision(
            request,
            Plan.EstadoPlan.APROBADO,
            "APROBAR",
        )

    @action(detail=True, methods=["post"])
    def rechazar(self, request, pk=None):
        return self._resolver_revision(
            request,
            Plan.EstadoPlan.RECHAZADO,
            "RECHAZAR",
            observacion_requerida=True,
        )

    def _resolver_revision(
        self,
        request,
        nuevo_estado,
        accion,
        observacion_requerida=False,
    ):
        if self.get_object().estado != Plan.EstadoPlan.EN_REVISION_INICIADA:
            return Response(
                {
                    "detail": (
                        "La decisión solo está permitida después de iniciar la revisión."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return self._transicionar(
            estados_origen={Plan.EstadoPlan.EN_REVISION_INICIADA},
            estado_nuevo=nuevo_estado,
            accion=accion,
            observacion=self._leer_observacion(request, observacion_requerida),
            validacion_requerida=(
                "aprobacion"
                if nuevo_estado == Plan.EstadoPlan.APROBADO
                else None
            ),
            requiere_revisor_actual=True,
            limpiar_revision=nuevo_estado
            in {
                Plan.EstadoPlan.DEVUELTO,
                Plan.EstadoPlan.RECHAZADO,
            },
            registrar_aprobacion=nuevo_estado == Plan.EstadoPlan.APROBADO,
        )

    @action(detail=True, methods=["post"])
    def archivar(self, request, pk=None):
        estados = {
            Plan.EstadoPlan.BORRADOR,
            Plan.EstadoPlan.DEVUELTO,
            Plan.EstadoPlan.RECHAZADO,
        }
        if request.user.tiene_permiso("planes.aprobar"):
            estados.add(Plan.EstadoPlan.APROBADO)
        return self._transicionar(
            estados_origen=estados,
            estado_nuevo=Plan.EstadoPlan.ARCHIVADO,
            accion="ARCHIVAR",
            observacion=self._leer_observacion(request),
            activo=False,
        )

    @action(detail=True, methods=["get"])
    def historial(self, request, pk=None):
        plan = self.get_object()
        eventos = plan.historial_estados.select_related("usuario").all()
        return Response(
            HistorialEstadoPlanSerializer(eventos, many=True).data,
            status=status.HTTP_200_OK,
        )

    def _construir_expediente(self, plan):
        metas = list(plan.metas.all())
        grupos = agrupar_metas_por_objetivo(metas)
        contexto = self.get_serializer_context()
        objetivos = []

        for objetivo_id, metas_objetivo in grupos.items():
            if objetivo_id is None:
                continue
            objetivo = metas_objetivo[0].objetivo_estrategico
            alineaciones = list(objetivo.alineaciones.all())
            seguimiento_objetivo = calcular_seguimiento_objetivo(
                objetivo,
                metas_objetivo,
            )
            metas_serializadas = []

            for meta in metas_objetivo:
                seguimiento_meta = calcular_seguimiento_meta(meta)
                indicadores_serializados = []
                for indicador in meta.indicadores.all():
                    seguimiento_indicador = calcular_seguimiento_indicador(
                        indicador
                    )
                    indicadores_serializados.append(
                        {
                            **IndicadorSerializer(
                                indicador,
                                context=contexto,
                            ).data,
                            **seguimiento_indicador,
                            "avances": AvanceIndicadorSerializer(
                                indicador.avances.all(),
                                many=True,
                                context=contexto,
                            ).data,
                        }
                    )

                metas_serializadas.append(
                    {
                        **MetaSerializer(meta, context=contexto).data,
                        **seguimiento_meta,
                        "indicadores": indicadores_serializados,
                    }
                )

            objetivos.append(
                {
                    "id": objetivo.pk,
                    "codigo": objetivo.codigo,
                    "nombre": objetivo.nombre,
                    "descripcion": objetivo.descripcion,
                    "estado": objetivo.estado,
                    **seguimiento_objetivo,
                    "alineaciones": AlineacionSerializer(
                        alineaciones,
                        many=True,
                        context=contexto,
                    ).data,
                    "metas": metas_serializadas,
                }
            )

        seguimiento = calcular_seguimiento_plan(plan)
        validacion = evaluar_integridad_plan(plan, metas)
        return {
            "plan": self.get_serializer(plan).data,
            "validacion": validacion,
            "progreso": seguimiento["progreso"],
            "estado_seguimiento": seguimiento["estado_seguimiento"],
            "etiqueta_estado_seguimiento": seguimiento[
                "etiqueta_estado_seguimiento"
            ],
            "resumen": seguimiento,
            "objetivos": objetivos,
            "historial": HistorialEstadoPlanSerializer(
                plan.historial_estados.all(),
                many=True,
            ).data,
        }

    @action(detail=True, methods=["get"])
    def expediente(self, request, pk=None):
        """Devuelve el contenido que sustenta una decisión de revisión."""

        return Response(
            self._construir_expediente(self.get_object()),
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def seguimiento(self, request, pk=None):
        """Consolida cumplimiento de objetivos, metas e indicadores."""

        expediente = self._construir_expediente(self.get_object())
        return Response(
            {
                "plan": expediente["plan"],
                "progreso": expediente["progreso"],
                "estado_seguimiento": expediente["estado_seguimiento"],
                "etiqueta_estado_seguimiento": expediente[
                    "etiqueta_estado_seguimiento"
                ],
                "resumen": expediente["resumen"],
                "objetivos": expediente["objetivos"],
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def validacion(self, request, pk=None):
        """Explica las condiciones que impiden enviar o aprobar el plan."""

        plan = self.get_object()
        return Response(
            evaluar_integridad_plan(plan, list(plan.metas.all())),
            status=status.HTTP_200_OK,
        )
