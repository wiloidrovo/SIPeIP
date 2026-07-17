from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.auditoria.services import (
    AuditoriaModelViewSetMixin,
    registrar_evento,
    serializar_instancia,
)
from apps.configuracion.scope import (
    filtrar_queryset_por_entidad,
    obtener_alcance_usuario,
)
from apps.planes.models import Plan
from apps.roles.permissions import HasSipeipPermission

from .models import AvanceIndicador, Indicador, Meta
from .serializers import (
    AvanceIndicadorSerializer,
    IndicadorSerializer,
    MetaSerializer,
    _validar_alcance_plan,
)


def _filtrar_propios(queryset, usuario, plan_lookup):
    if obtener_alcance_usuario(usuario) not in {"ENTIDAD", "PROPIO_ASIGNADO"}:
        return queryset
    return queryset.filter(
        Q(**{f"{plan_lookup}__creado_por": usuario})
        | Q(**{f"{plan_lookup}__responsable": usuario})
    )


class MetaViewSet(AuditoriaModelViewSetMixin, viewsets.ModelViewSet):
    """
    API REST para gestionar metas institucionales asociadas a planes.
    """

    queryset = Meta.objects.select_related("plan").all()
    serializer_class = MetaSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "metas.ver",
        "retrieve": "metas.ver",
        "create": "metas.crear",
        "update": "metas.editar",
        "partial_update": "metas.editar",
        "destroy": "metas.eliminar",
        "activar": "metas.editar",
        "cerrar": "metas.editar",
        "archivar": "metas.archivar",
    }
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "nombre",
        "descripcion",
        "resultado_esperado",
        "estado",
        "plan__nombre",
    ]
    ordering_fields = ["id", "nombre", "estado", "fecha_inicio", "fecha_fin"]
    ordering = ["-fecha_creacion"]
    audit_modulo = "metas"
    audit_funcionalidad = "metas institucionales"

    def get_queryset(self):
        queryset = filtrar_queryset_por_entidad(
            super().get_queryset(), self.request.user, "plan__entidad"
        )
        return _filtrar_propios(queryset, self.request.user, "plan").distinct()

    @staticmethod
    def _validar_plan_editable(plan):
        if not plan.activo or plan.estado not in {
            Plan.EstadoPlan.BORRADOR,
            Plan.EstadoPlan.DEVUELTO,
            Plan.EstadoPlan.RECHAZADO,
        }:
            raise serializers.ValidationError(
                {"plan": "Solo se pueden gestionar metas de un plan editable."}
            )

    def _bloquear_planes_relacionados(self, meta, plan_adicional=None):
        ids = {meta.plan_id}
        if plan_adicional:
            ids.add(plan_adicional)
        planes = {
            plan.pk: plan
            for plan in Plan.objects.select_for_update()
            .filter(pk__in=ids)
            .order_by("pk")
        }
        meta.plan = planes[meta.plan_id]
        if not self.get_queryset().filter(pk=meta.pk).exists():
            raise NotFound("La meta no existe dentro de su alcance.")
        return planes

    @transaction.atomic
    def perform_create(self, serializer):
        plan = Plan.objects.select_for_update().get(
            pk=serializer.validated_data["plan"].pk
        )
        self._validar_plan_editable(plan)
        _validar_alcance_plan(serializer, plan)
        serializer.validated_data["plan"] = plan
        super().perform_create(serializer)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """
        Evita eliminar metas que ya tienen indicadores asociados.
        """

        meta_autorizada = self.get_object()
        meta = self._obtener_instancia_bloqueada(meta_autorizada)
        self._bloquear_planes_relacionados(meta)
        try:
            self._validar_plan_editable(meta.plan)
        except serializers.ValidationError:
            return Response(
                {"detail": "No puede eliminar metas de un plan no editable."},
                status=status.HTTP_409_CONFLICT,
            )
        indicadores_count = meta.indicadores.count()

        if indicadores_count > 0:
            return Response(
                {
                    "detail": (
                        f"No se puede eliminar la meta '{meta.nombre}' porque "
                        f"tiene {indicadores_count} indicador(es) asociado(s). "
                        "Elimine o reasigne los indicadores antes de continuar."
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
                        "No se puede eliminar esta meta porque está vinculada "
                        "a otros registros del sistema."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        meta_autorizada = self.get_object()
        meta = self._obtener_instancia_bloqueada(meta_autorizada)
        plan_solicitado = request.data.get("plan")
        plan_adicional = (
            int(plan_solicitado)
            if str(plan_solicitado).isdigit()
            else None
        )
        self._bloquear_planes_relacionados(meta, plan_adicional)
        if meta.estado in {Meta.EstadoMeta.CERRADA, Meta.EstadoMeta.ARCHIVADA}:
            return Response(
                {"detail": "La meta no puede editarse en su estado actual."},
                status=status.HTTP_409_CONFLICT,
            )
        if meta.plan.estado not in {
            Plan.EstadoPlan.BORRADOR,
            Plan.EstadoPlan.DEVUELTO,
            Plan.EstadoPlan.RECHAZADO,
        }:
            return Response(
                {"detail": "No puede editar metas de un plan no editable."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def archivar(self, request, pk=None):
        """Archiva una meta sin eliminarla físicamente."""

        meta_autorizada = self.get_object()
        meta = self._obtener_instancia_bloqueada(meta_autorizada)
        self._bloquear_planes_relacionados(meta)

        if meta.estado == Meta.EstadoMeta.ARCHIVADA:
            return Response(
                {"detail": "La meta ya se encuentra archivada."},
                status=status.HTTP_409_CONFLICT,
            )

        antes = serializar_instancia(meta)
        meta.estado = Meta.EstadoMeta.ARCHIVADA
        meta.activa = False
        meta.save(update_fields=["estado", "activa", "fecha_actualizacion"])
        registrar_evento(
            request=request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="ARCHIVAR",
            instancia=meta,
            antes=antes,
        )

        serializer = self.get_serializer(meta)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def activar(self, request, pk=None):
        """Activa una meta que todavía se encuentra en borrador."""

        meta_autorizada = self.get_object()
        meta = self._obtener_instancia_bloqueada(meta_autorizada)
        self._bloquear_planes_relacionados(meta)

        if meta.estado != Meta.EstadoMeta.BORRADOR:
            return Response(
                {"detail": "Solo una meta en borrador puede activarse."},
                status=status.HTTP_409_CONFLICT,
            )

        if not meta.plan.activo or meta.plan.estado == Plan.EstadoPlan.ARCHIVADO:
            return Response(
                {
                    "detail": (
                        "No se puede activar una meta cuyo plan está "
                        "inactivo o archivado."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        if meta.plan.estado not in {
            Plan.EstadoPlan.BORRADOR,
            Plan.EstadoPlan.DEVUELTO,
            Plan.EstadoPlan.RECHAZADO,
        }:
            return Response(
                {"detail": "Solo se puede activar una meta de un plan editable."},
                status=status.HTTP_409_CONFLICT,
            )

        antes = serializar_instancia(meta)
        meta.estado = Meta.EstadoMeta.ACTIVA
        meta.activa = True
        meta.save(update_fields=["estado", "activa", "fecha_actualizacion"])
        registrar_evento(
            request=request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="ACTIVAR",
            instancia=meta,
            antes=antes,
        )

        serializer = self.get_serializer(meta)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def cerrar(self, request, pk=None):
        """Cierra una meta activa sin eliminar su trazabilidad."""

        meta_autorizada = self.get_object()
        meta = self._obtener_instancia_bloqueada(meta_autorizada)
        self._bloquear_planes_relacionados(meta)

        if meta.estado != Meta.EstadoMeta.ACTIVA:
            return Response(
                {"detail": "Solo una meta activa puede cerrarse."},
                status=status.HTTP_409_CONFLICT,
            )

        antes = serializar_instancia(meta)
        meta.estado = Meta.EstadoMeta.CERRADA
        meta.activa = False
        meta.save(update_fields=["estado", "activa", "fecha_actualizacion"])
        registrar_evento(
            request=request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="CERRAR",
            instancia=meta,
            antes=antes,
        )

        serializer = self.get_serializer(meta)
        return Response(serializer.data, status=status.HTTP_200_OK)


class IndicadorViewSet(AuditoriaModelViewSetMixin, viewsets.ModelViewSet):
    """
    API REST para gestionar indicadores y registrar avances de medición.
    """

    queryset = Indicador.objects.select_related("meta", "meta__plan").all()
    serializer_class = IndicadorSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "indicadores.ver",
        "retrieve": "indicadores.ver",
        "create": "indicadores.crear",
        "update": "indicadores.editar",
        "partial_update": "indicadores.editar",
        "destroy": "indicadores.eliminar",
        "registrar_avance": "indicadores.registrar_avance",
        "activar": "indicadores.editar",
        "desactivar": "indicadores.editar",
        "validar": "indicadores.validar",
    }
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "nombre",
        "descripcion",
        "unidad_medida",
        "frecuencia",
        "meta__nombre",
        "meta__plan__nombre",
    ]
    ordering_fields = [
        "id",
        "nombre",
        "valor_actual",
        "valor_meta",
        "frecuencia",
        "fecha_creacion",
    ]
    ordering = ["-fecha_creacion"]
    audit_modulo = "indicadores"
    audit_funcionalidad = "indicadores"

    def get_queryset(self):
        queryset = filtrar_queryset_por_entidad(
            super().get_queryset(), self.request.user, "meta__plan__entidad"
        )
        return _filtrar_propios(
            queryset, self.request.user, "meta__plan"
        ).distinct()

    @staticmethod
    def _validar_meta_editable(meta):
        if not meta.activa or meta.estado != Meta.EstadoMeta.ACTIVA:
            raise serializers.ValidationError(
                {"meta": "Solo se pueden gestionar indicadores de una meta activa."}
            )
        MetaViewSet._validar_plan_editable(meta.plan)

    def _bloquear_jerarquia(self, indicador, meta_adicional=None):
        meta_ids = {indicador.meta_id}
        if meta_adicional:
            meta_ids.add(meta_adicional)
        metas = {
            meta.pk: meta
            for meta in Meta.objects.select_for_update()
            .filter(pk__in=meta_ids)
            .order_by("pk")
        }
        plan_ids = {meta.plan_id for meta in metas.values()}
        planes = {
            plan.pk: plan
            for plan in Plan.objects.select_for_update()
            .filter(pk__in=plan_ids)
            .order_by("pk")
        }
        for meta in metas.values():
            meta.plan = planes[meta.plan_id]
        indicador.meta = metas[indicador.meta_id]
        if not self.get_queryset().filter(pk=indicador.pk).exists():
            raise NotFound("El indicador no existe dentro de su alcance.")
        return metas

    @transaction.atomic
    def perform_create(self, serializer):
        meta = Meta.objects.select_for_update().get(
            pk=serializer.validated_data["meta"].pk
        )
        plan = Plan.objects.select_for_update().get(pk=meta.plan_id)
        meta.plan = plan
        self._validar_meta_editable(meta)
        _validar_alcance_plan(serializer, plan)
        serializer.validated_data["meta"] = meta
        super().perform_create(serializer)

    @staticmethod
    def _conflicto_jerarquia(indicador):
        meta = indicador.meta
        plan = meta.plan

        if not meta.activa or meta.estado != Meta.EstadoMeta.ACTIVA:
            return Response(
                {
                    "detail": (
                        "No se puede operar el indicador porque su meta "
                        "no está activa."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        if not plan.activo or plan.estado == Plan.EstadoPlan.ARCHIVADO:
            return Response(
                {
                    "detail": (
                        "No se puede operar el indicador porque su plan "
                        "está inactivo o archivado."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return None

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        indicador_autorizado = self.get_object()
        indicador = self._obtener_instancia_bloqueada(indicador_autorizado)
        meta_solicitada = request.data.get("meta")
        meta_adicional = (
            int(meta_solicitada)
            if str(meta_solicitada).isdigit()
            else None
        )
        self._bloquear_jerarquia(indicador, meta_adicional)
        if indicador.validado:
            return Response(
                {"detail": "Un indicador validado no puede modificarse."},
                status=status.HTTP_409_CONFLICT,
            )
        if indicador.meta.plan.estado not in {
            Plan.EstadoPlan.BORRADOR,
            Plan.EstadoPlan.DEVUELTO,
            Plan.EstadoPlan.RECHAZADO,
        }:
            return Response(
                {"detail": "No puede editar indicadores de un plan no editable."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """
        Evita eliminar indicadores que ya tienen avances registrados.
        """

        indicador_autorizado = self.get_object()
        indicador = self._obtener_instancia_bloqueada(indicador_autorizado)
        self._bloquear_jerarquia(indicador)
        try:
            self._validar_meta_editable(indicador.meta)
        except serializers.ValidationError:
            return Response(
                {"detail": "No puede eliminar indicadores de un plan no editable."},
                status=status.HTTP_409_CONFLICT,
            )
        avances_count = indicador.avances.count()

        if avances_count > 0:
            return Response(
                {
                    "detail": (
                        f"No se puede eliminar el indicador '{indicador.nombre}' "
                        f"porque tiene {avances_count} avance(s) registrado(s). "
                        "Desactive el indicador si ya no debe utilizarse."
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
                        "No se puede eliminar este indicador porque está "
                        "vinculado a otros registros del sistema."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

    @action(detail=True, methods=["post"], url_path="registrar-avance")
    def registrar_avance(self, request, pk=None):
        """
        Registra un avance y actualiza el valor actual del indicador.
        """

        indicador_autorizado = self.get_object()

        with transaction.atomic():
            indicador = self._obtener_instancia_bloqueada(indicador_autorizado)
            self._bloquear_jerarquia(indicador)
            conflicto = self._conflicto_jerarquia(indicador)

            if conflicto is not None:
                return conflicto

            data = request.data.copy()
            data["indicador"] = indicador.id

            serializer = AvanceIndicadorSerializer(
                data=data,
                context=self.get_serializer_context(),
            )
            serializer.is_valid(raise_exception=True)
            avance = serializer.save(registrado_por=request.user)

            antes = serializar_instancia(indicador)
            ultimo_avance = indicador.avances.order_by(
                "-fecha_registro", "-fecha_creacion", "-id"
            ).first()
            if ultimo_avance and ultimo_avance.pk == avance.pk:
                indicador.valor_actual = avance.valor
                indicador.save(
                    update_fields=["valor_actual", "fecha_actualizacion"]
                )
                registrar_evento(
                    request=request,
                    modulo=self.audit_modulo,
                    funcionalidad=self.audit_funcionalidad,
                    accion="ACTUALIZAR_VALOR",
                    instancia=indicador,
                    antes=antes,
                )
            registrar_evento(
                request=request,
                modulo="avances",
                funcionalidad="avances de indicadores",
                accion="REGISTRAR_AVANCE",
                instancia=avance,
            )

        response_serializer = AvanceIndicadorSerializer(
            avance,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def activar(self, request, pk=None):
        """
        Activa un indicador para permitir nuevos registros de avance.
        """

        indicador_autorizado = self.get_object()
        indicador = self._obtener_instancia_bloqueada(indicador_autorizado)
        self._bloquear_jerarquia(indicador)
        conflicto = self._conflicto_jerarquia(indicador)

        if conflicto is not None:
            return conflicto
        if indicador.activo:
            return Response(
                {"detail": "El indicador ya se encuentra activo."},
                status=status.HTTP_409_CONFLICT,
            )

        antes = serializar_instancia(indicador)
        indicador.activo = True
        indicador.save(update_fields=["activo", "fecha_actualizacion"])
        registrar_evento(
            request=request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="ACTIVAR",
            instancia=indicador,
            antes=antes,
        )

        serializer = self.get_serializer(indicador)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def desactivar(self, request, pk=None):
        """
        Desactiva un indicador sin eliminar sus avances históricos.
        """

        indicador_autorizado = self.get_object()
        indicador = self._obtener_instancia_bloqueada(indicador_autorizado)
        self._bloquear_jerarquia(indicador)
        if not indicador.activo:
            return Response(
                {"detail": "El indicador ya se encuentra inactivo."},
                status=status.HTTP_409_CONFLICT,
            )
        antes = serializar_instancia(indicador)
        indicador.activo = False
        indicador.save(update_fields=["activo", "fecha_actualizacion"])
        registrar_evento(
            request=request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="DESACTIVAR",
            instancia=indicador,
            antes=antes,
        )

        serializer = self.get_serializer(indicador)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def validar(self, request, pk=None):
        indicador_autorizado = self.get_object()
        indicador = self._obtener_instancia_bloqueada(indicador_autorizado)
        self._bloquear_jerarquia(indicador)
        if indicador.validado:
            return Response(
                {"detail": "El indicador ya se encuentra validado."},
                status=status.HTTP_409_CONFLICT,
            )
        if not indicador.activo:
            return Response(
                {"detail": "Solo se puede validar un indicador activo."},
                status=status.HTTP_409_CONFLICT,
            )
        conflicto = self._conflicto_jerarquia(indicador)
        if conflicto is not None:
            return conflicto

        antes = serializar_instancia(indicador)
        indicador.validado = True
        indicador.validado_por = request.user
        indicador.fecha_validacion = timezone.now()
        indicador.save(
            update_fields=[
                "validado",
                "validado_por",
                "fecha_validacion",
                "fecha_actualizacion",
            ]
        )
        registrar_evento(
            request=request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="VALIDAR",
            instancia=indicador,
            antes=antes,
        )
        return Response(self.get_serializer(indicador).data)


class AvanceIndicadorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API de solo lectura para consultar avances registrados.

    La creación de avances se realiza desde la acción registrar-avance del
    indicador para garantizar que el valor actual se actualice correctamente.
    """

    queryset = AvanceIndicador.objects.select_related(
        "indicador",
        "indicador__meta",
        "registrado_por",
    ).all()
    serializer_class = AvanceIndicadorSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "indicadores.ver",
        "retrieve": "indicadores.ver",
    }
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "indicador__nombre",
        "indicador__meta__nombre",
        "observacion",
    ]
    ordering_fields = ["id", "fecha_registro", "valor", "fecha_creacion"]
    ordering = ["-fecha_registro", "-fecha_creacion"]

    def get_queryset(self):
        queryset = filtrar_queryset_por_entidad(
            super().get_queryset(),
            self.request.user,
            "indicador__meta__plan__entidad",
        )
        return _filtrar_propios(
            queryset, self.request.user, "indicador__meta__plan"
        ).distinct()
