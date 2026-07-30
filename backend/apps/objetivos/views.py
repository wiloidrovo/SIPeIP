from django.db import transaction
from django.db.models import Count, Prefetch, Subquery
from django.db.models.deletion import ProtectedError
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.auditoria.services import (
    AuditoriaModelViewSetMixin,
    registrar_evento,
    serializar_instancia,
)
from apps.metas.models import Meta
from apps.planes.models import Plan
from apps.roles.permissions import HasSipeipPermission

from .models import Alineacion, EjePND, EstadoCatalogo, ObjetivoEstrategico, ObjetivoPND, ODS
from .scope import filtrar_alineaciones_por_alcance, filtrar_objetivos_por_alcance
from .serializers import (
    AlineacionSerializer,
    EjePNDSerializer,
    ObjetivoEstrategicoSerializer,
    ObjetivoPNDSerializer,
    ODSSerializer,
)


ESTADOS_EXPEDIENTE_INMUTABLE = frozenset(
    {
        Plan.EstadoPlan.EN_REVISION,
        Plan.EstadoPlan.EN_REVISION_INICIADA,
        Plan.EstadoPlan.APROBADO,
        Plan.EstadoPlan.ARCHIVADO,
    }
)


def _respuesta_expediente_inmutable(plan):
    return Response(
        {
            "code": "expediente_inmutable",
            "detail": (
                "No se puede modificar este registro porque forma parte del "
                f"expediente «{plan.nombre}» en estado {plan.estado}. "
                "Devuelva el plan a edición o cree una nueva versión del "
                "catálogo para preservar la decisión y su trazabilidad."
            ),
            "plan_id": plan.pk,
            "plan_estado": plan.estado,
        },
        status=status.HTTP_409_CONFLICT,
    )


def _primer_plan_bloqueado(**filtros):
    """Bloquea un plan relacionado sin combinar FOR UPDATE con DISTINCT.

    PostgreSQL no admite ``SELECT ... FOR UPDATE`` cuando el SELECT exterior
    contiene ``DISTINCT``. Las relaciones inversas pueden duplicar planes, por
    lo que primero se deduplican sus identificadores en una subconsulta y luego
    se bloquea la fila real del plan en la consulta exterior.
    """

    planes_relacionados = (
        Plan.objects.filter(**filtros)
        .values("pk")
        .distinct()
    )
    return (
        Plan.objects.select_for_update()
        .filter(pk__in=Subquery(planes_relacionados))
        .order_by("pk")
        .first()
    )


class ExpedienteInmutableMixin:
    """Impide alterar catálogos consumidos por expedientes no editables."""

    plan_lookup_bloqueo = None

    def _primer_plan_bloqueado(self, instancia):
        if not self.plan_lookup_bloqueo:
            return None
        return _primer_plan_bloqueado(
            **{
                self.plan_lookup_bloqueo: instancia,
                "estado__in": ESTADOS_EXPEDIENTE_INMUTABLE,
            }
        )

    def _verificar_expediente_mutable(self, instancia):
        plan = self._primer_plan_bloqueado(instancia)
        return _respuesta_expediente_inmutable(plan) if plan else None

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instancia = self.get_object()
        conflicto = self._verificar_expediente_mutable(instancia)
        if conflicto is not None:
            return conflicto
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instancia = self.get_object()
        conflicto = self._verificar_expediente_mutable(instancia)
        if conflicto is not None:
            return conflicto
        return super().destroy(request, *args, **kwargs)


class EliminacionProtegidaMixin:
    mensaje_eliminacion_protegida = (
        "No se puede eliminar el registro porque mantiene relaciones trazables."
    )

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": self.mensaje_eliminacion_protegida},
                status=status.HTTP_409_CONFLICT,
            )


class AccionesEstadoCatalogoMixin:
    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        return self._cambiar_estado_catalogo(EstadoCatalogo.ACTIVO, "ACTIVAR")

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        return self._cambiar_estado_catalogo(EstadoCatalogo.INACTIVO, "DESACTIVAR")

    @transaction.atomic
    def _cambiar_estado_catalogo(self, nuevo_estado, accion_auditoria):
        instancia_autorizada = self.get_object()
        verificar = getattr(self, "_verificar_expediente_mutable", None)
        if verificar is not None:
            conflicto = verificar(instancia_autorizada)
            if conflicto is not None:
                return conflicto
        instancia = self._obtener_instancia_bloqueada(instancia_autorizada)
        if instancia.estado == nuevo_estado:
            etiqueta = dict(EstadoCatalogo.choices)[nuevo_estado].lower()
            return Response(
                {"detail": f"El registro ya se encuentra {etiqueta}."},
                status=status.HTTP_409_CONFLICT,
            )

        antes = serializar_instancia(instancia)
        instancia.estado = nuevo_estado
        instancia.save(update_fields=["estado", "fecha_actualizacion"])
        registrar_evento(
            request=self.request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion=accion_auditoria,
            instancia=instancia,
            antes=antes,
        )
        return Response(self.get_serializer(instancia).data)


class ObjetivoEstrategicoViewSet(
    ExpedienteInmutableMixin,
    EliminacionProtegidaMixin,
    AccionesEstadoCatalogoMixin,
    AuditoriaModelViewSetMixin,
    viewsets.ModelViewSet,
):
    plan_lookup_bloqueo = "metas__objetivo_estrategico"
    serializer_class = ObjetivoEstrategicoSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "objetivos.ver",
        "retrieve": "objetivos.ver",
        "create": "objetivos.gestionar",
        "update": "objetivos.gestionar",
        "partial_update": "objetivos.gestionar",
        "destroy": "objetivos.gestionar",
        "activar": "objetivos.gestionar",
        "desactivar": "objetivos.gestionar",
    }
    audit_modulo = "objetivos"
    audit_funcionalidad = "objetivos estratégicos"
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["codigo", "nombre", "descripcion", "entidad__nombre"]
    ordering_fields = [
        "id",
        "codigo",
        "nombre",
        "estado",
        "fecha_creacion",
        "fecha_actualizacion",
    ]
    ordering = ["entidad__nombre", "codigo"]
    mensaje_eliminacion_protegida = (
        "No se puede eliminar el objetivo porque está vinculado a alineaciones, "
        "proyectos u otros registros trazables."
    )

    def get_queryset(self):
        queryset = (
            ObjetivoEstrategico.objects.select_related("entidad")
            .prefetch_related("alineaciones__ods")
            .annotate(
                metas_count_anotado=Count("metas", distinct=True),
                planes_count_anotado=Count("metas__plan", distinct=True),
                alineaciones_count_anotado=Count("alineaciones", distinct=True),
            )
        )
        queryset = filtrar_objetivos_por_alcance(queryset, self.request.user)
        entidad = self.request.query_params.get("entidad")
        estado_filtro = self.request.query_params.get("estado")
        if entidad and entidad.isdigit():
            queryset = queryset.filter(entidad_id=int(entidad))
        if estado_filtro in EstadoCatalogo.values:
            queryset = queryset.filter(estado=estado_filtro)
        return queryset


class EjePNDViewSet(
    ExpedienteInmutableMixin,
    EliminacionProtegidaMixin,
    AccionesEstadoCatalogoMixin,
    AuditoriaModelViewSetMixin,
    viewsets.ModelViewSet,
):
    plan_lookup_bloqueo = (
        "metas__objetivo_estrategico__alineaciones__objetivo_pnd__eje"
    )
    queryset = EjePND.objects.all()
    serializer_class = EjePNDSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "alineaciones.ver",
        "retrieve": "alineaciones.ver",
        "create": "alineaciones.gestionar_catalogos",
        "update": "alineaciones.gestionar_catalogos",
        "partial_update": "alineaciones.gestionar_catalogos",
        "destroy": "alineaciones.gestionar_catalogos",
        "activar": "alineaciones.gestionar_catalogos",
        "desactivar": "alineaciones.gestionar_catalogos",
    }
    audit_modulo = "alineacion"
    audit_funcionalidad = "ejes PND"
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["codigo", "nombre", "descripcion"]
    ordering_fields = [
        "id",
        "codigo",
        "nombre",
        "estado",
        "fecha_creacion",
        "fecha_actualizacion",
    ]
    ordering = ["codigo"]
    mensaje_eliminacion_protegida = (
        "No se puede eliminar el eje PND porque contiene objetivos vinculados."
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        estado_filtro = self.request.query_params.get("estado")
        if estado_filtro in EstadoCatalogo.values:
            queryset = queryset.filter(estado=estado_filtro)
        return queryset


class ObjetivoPNDViewSet(
    ExpedienteInmutableMixin,
    EliminacionProtegidaMixin,
    AccionesEstadoCatalogoMixin,
    AuditoriaModelViewSetMixin,
    viewsets.ModelViewSet,
):
    plan_lookup_bloqueo = (
        "metas__objetivo_estrategico__alineaciones__objetivo_pnd"
    )
    serializer_class = ObjetivoPNDSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "alineaciones.ver",
        "retrieve": "alineaciones.ver",
        "create": "alineaciones.gestionar_catalogos",
        "update": "alineaciones.gestionar_catalogos",
        "partial_update": "alineaciones.gestionar_catalogos",
        "destroy": "alineaciones.gestionar_catalogos",
        "activar": "alineaciones.gestionar_catalogos",
        "desactivar": "alineaciones.gestionar_catalogos",
    }
    audit_modulo = "alineacion"
    audit_funcionalidad = "objetivos PND"
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["codigo", "nombre", "descripcion", "eje__codigo", "eje__nombre"]
    ordering_fields = [
        "id",
        "codigo",
        "nombre",
        "estado",
        "fecha_creacion",
        "fecha_actualizacion",
    ]
    ordering = ["eje__codigo", "codigo"]
    mensaje_eliminacion_protegida = (
        "No se puede eliminar el objetivo PND porque mantiene alineaciones."
    )

    def get_queryset(self):
        queryset = ObjetivoPND.objects.select_related("eje")
        eje = self.request.query_params.get("eje")
        estado_filtro = self.request.query_params.get("estado")
        if eje and eje.isdigit():
            queryset = queryset.filter(eje_id=int(eje))
        if estado_filtro in EstadoCatalogo.values:
            queryset = queryset.filter(estado=estado_filtro)
        return queryset


class ODSViewSet(
    ExpedienteInmutableMixin,
    EliminacionProtegidaMixin,
    AccionesEstadoCatalogoMixin,
    AuditoriaModelViewSetMixin,
    viewsets.ModelViewSet,
):
    plan_lookup_bloqueo = "metas__objetivo_estrategico__alineaciones__ods"
    queryset = ODS.objects.all()
    serializer_class = ODSSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "alineaciones.ver",
        "retrieve": "alineaciones.ver",
        "create": "alineaciones.gestionar_catalogos",
        "update": "alineaciones.gestionar_catalogos",
        "partial_update": "alineaciones.gestionar_catalogos",
        "destroy": "alineaciones.gestionar_catalogos",
        "activar": "alineaciones.gestionar_catalogos",
        "desactivar": "alineaciones.gestionar_catalogos",
    }
    audit_modulo = "alineacion"
    audit_funcionalidad = "catálogo ODS"
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["numero", "nombre", "descripcion"]
    ordering_fields = [
        "id",
        "numero",
        "nombre",
        "estado",
        "fecha_creacion",
        "fecha_actualizacion",
    ]
    ordering = ["numero"]
    mensaje_eliminacion_protegida = (
        "No se puede eliminar el ODS porque mantiene alineaciones."
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        estado_filtro = self.request.query_params.get("estado")
        if estado_filtro in EstadoCatalogo.values:
            queryset = queryset.filter(estado=estado_filtro)
        return queryset


class AlineacionViewSet(
    EliminacionProtegidaMixin,
    AuditoriaModelViewSetMixin,
    viewsets.ModelViewSet,
):
    serializer_class = AlineacionSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "alineaciones.ver",
        "retrieve": "alineaciones.ver",
        "create": "alineaciones.gestionar",
        "update": "alineaciones.gestionar",
        "partial_update": "alineaciones.gestionar",
        "destroy": "alineaciones.gestionar",
        "reabrir": "alineaciones.gestionar",
        "validar": "alineaciones.validar",
        "rechazar": "alineaciones.validar",
    }
    audit_modulo = "alineacion"
    audit_funcionalidad = "matriz PND/ODS"
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "objetivo_estrategico__codigo",
        "objetivo_estrategico__nombre",
        "objetivo_pnd__codigo",
        "objetivo_pnd__nombre",
        "ods__nombre",
        "justificacion",
        "usuario_creador__username",
        "usuario_validador__username",
    ]
    ordering_fields = [
        "id",
        "estado",
        "fecha_creacion",
        "fecha_actualizacion",
    ]
    ordering = ["-fecha_actualizacion", "-id"]
    mensaje_eliminacion_protegida = (
        "No se puede eliminar la alineación porque mantiene registros trazables."
    )

    def _verificar_alineacion_mutable(self, alineacion):
        plan = _primer_plan_bloqueado(
            metas__objetivo_estrategico_id=(
                alineacion.objetivo_estrategico_id
            ),
            estado__in=ESTADOS_EXPEDIENTE_INMUTABLE,
        )
        return _respuesta_expediente_inmutable(plan) if plan else None

    def get_queryset(self):
        queryset = Alineacion.objects.select_related(
            "objetivo_estrategico__entidad",
            "objetivo_pnd__eje",
            "ods",
            "usuario_creador",
            "usuario_validador",
        ).prefetch_related(
            Prefetch(
                "objetivo_estrategico__metas",
                queryset=Meta.objects.prefetch_related("indicadores"),
            )
        )
        queryset = filtrar_alineaciones_por_alcance(
            queryset,
            self.request.user,
        )

        filtros_numericos = {
            "entidad": "objetivo_estrategico__entidad_id",
            "objetivo_estrategico": "objetivo_estrategico_id",
            "objetivo_pnd": "objetivo_pnd_id",
            "ods": "ods_id",
        }
        for parametro, lookup in filtros_numericos.items():
            valor = self.request.query_params.get(parametro)
            if valor and valor.isdigit():
                queryset = queryset.filter(**{lookup: int(valor)})

        estado_filtro = self.request.query_params.get("estado")
        if estado_filtro in Alineacion.EstadoAlineacion.values:
            queryset = queryset.filter(estado=estado_filtro)
        return queryset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        objetivo = serializer.validated_data["objetivo_estrategico"]
        plan = _primer_plan_bloqueado(
            metas__objetivo_estrategico=objetivo,
            estado__in=ESTADOS_EXPEDIENTE_INMUTABLE,
        )
        if plan:
            return _respuesta_expediente_inmutable(plan)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @transaction.atomic
    def perform_create(self, serializer):
        instancia = serializer.save(usuario_creador=self.request.user)
        registrar_evento(
            request=self.request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="CREAR",
            instancia=instancia,
            entidad=instancia.entidad,
        )

    @transaction.atomic
    def perform_update(self, serializer):
        antes = serializar_instancia(serializer.instance)
        instancia = serializer.save()
        registrar_evento(
            request=self.request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="EDITAR",
            instancia=instancia,
            antes=antes,
            entidad=instancia.entidad,
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        alineacion_autorizada = self.get_object()
        conflicto = self._verificar_alineacion_mutable(
            alineacion_autorizada
        )
        if conflicto is not None:
            return conflicto
        alineacion = Alineacion.objects.select_for_update().get(
            pk=alineacion_autorizada.pk
        )
        if alineacion.estado != Alineacion.EstadoAlineacion.BORRADOR:
            return Response(
                {"detail": "Solo se puede editar una alineación en estado borrador."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        alineacion_autorizada = self.get_object()
        conflicto = self._verificar_alineacion_mutable(
            alineacion_autorizada
        )
        if conflicto is not None:
            return conflicto
        alineacion = Alineacion.objects.select_for_update().get(
            pk=alineacion_autorizada.pk
        )
        if alineacion.estado != Alineacion.EstadoAlineacion.BORRADOR:
            return Response(
                {
                    "detail": (
                        "Solo se puede eliminar una alineación en estado borrador."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def validar(self, request, pk=None):
        return self._resolver(
            Alineacion.EstadoAlineacion.VALIDADA,
            "VALIDAR",
        )

    @action(detail=True, methods=["post"])
    def rechazar(self, request, pk=None):
        return self._resolver(
            Alineacion.EstadoAlineacion.RECHAZADA,
            "RECHAZAR",
        )

    @action(detail=True, methods=["post"])
    def reabrir(self, request, pk=None):
        with transaction.atomic():
            alineacion_autorizada = self.get_object()
            conflicto = self._verificar_alineacion_mutable(
                alineacion_autorizada
            )
            if conflicto is not None:
                return conflicto
            alineacion = self._obtener_instancia_bloqueada(
                alineacion_autorizada
            )
            if alineacion.estado != Alineacion.EstadoAlineacion.RECHAZADA:
                return Response(
                    {
                        "detail": (
                            "Solo se puede reabrir una alineación rechazada."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            antes = serializar_instancia(alineacion)
            alineacion.estado = Alineacion.EstadoAlineacion.BORRADOR
            alineacion.usuario_validador = None
            alineacion.save(
                update_fields=[
                    "estado",
                    "usuario_validador",
                    "fecha_actualizacion",
                ]
            )
            registrar_evento(
                request=self.request,
                modulo=self.audit_modulo,
                funcionalidad=self.audit_funcionalidad,
                accion="REABRIR",
                instancia=alineacion,
                antes=antes,
                entidad=alineacion.entidad,
            )
        return Response(self.get_serializer(alineacion).data)

    def _resolver(self, nuevo_estado, accion_auditoria):
        with transaction.atomic():
            alineacion = self._obtener_bloqueada()
            if alineacion.estado != Alineacion.EstadoAlineacion.BORRADOR:
                return Response(
                    {
                        "detail": (
                            "Solo se puede resolver una alineación en estado borrador."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            if not (
                self.request.user.is_superuser
                and self.request.user.is_active
            ):
                revision_asignada = Plan.objects.filter(
                    metas__objetivo_estrategico=(
                        alineacion.objetivo_estrategico
                    ),
                    estado=Plan.EstadoPlan.EN_REVISION_INICIADA,
                    revisor=self.request.user,
                ).exists()
                if not revision_asignada:
                    return Response(
                        {
                            "code": "revision_asignada",
                            "detail": (
                                "La alineación solo puede resolverla el "
                                "supervisor asignado a la revisión del plan."
                            ),
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

            if (
                alineacion.objetivo_estrategico.estado != EstadoCatalogo.ACTIVO
                or alineacion.objetivo_pnd.estado != EstadoCatalogo.ACTIVO
                or alineacion.objetivo_pnd.eje.estado != EstadoCatalogo.ACTIVO
                or alineacion.ods.estado != EstadoCatalogo.ACTIVO
            ):
                return Response(
                    {
                        "detail": (
                            "No se puede resolver la alineación porque contiene "
                            "un objetivo o catálogo inactivo."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            antes = serializar_instancia(alineacion)
            alineacion.estado = nuevo_estado
            alineacion.usuario_validador = self.request.user
            alineacion.save(
                update_fields=[
                    "estado",
                    "usuario_validador",
                    "fecha_actualizacion",
                ]
            )
            registrar_evento(
                request=self.request,
                modulo=self.audit_modulo,
                funcionalidad=self.audit_funcionalidad,
                accion=accion_auditoria,
                instancia=alineacion,
                antes=antes,
                entidad=alineacion.entidad,
            )
        return Response(self.get_serializer(alineacion).data)

    def _obtener_bloqueada(self):
        alineacion_autorizada = self.get_object()
        return self._obtener_instancia_bloqueada(alineacion_autorizada)
