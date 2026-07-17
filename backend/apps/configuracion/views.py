from django.db import transaction
from django.db.models import Count
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.auditoria.services import (
    AuditoriaModelViewSetMixin,
    registrar_evento,
    serializar_instancia,
)
from apps.roles.permissions import HasSipeipPermission

from .models import EntidadInstitucional, UnidadOrganizacional
from .scope import filtrar_queryset_por_entidad, tiene_alcance_global
from .serializers import (
    EntidadInstitucionalSerializer,
    UnidadOrganizacionalSerializer,
)


class EntidadInstitucionalViewSet(
    AuditoriaModelViewSetMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = EntidadInstitucionalSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "configuracion.ver",
        "retrieve": "configuracion.ver",
        "create": "configuracion.gestionar",
        "update": "configuracion.gestionar",
        "partial_update": "configuracion.gestionar",
        "activar": "configuracion.gestionar",
        "desactivar": "configuracion.gestionar",
    }
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["codigo_oficial", "nombre", "subsector", "nivel_gobierno"]
    ordering_fields = [
        "id",
        "codigo_oficial",
        "nombre",
        "estado",
        "fecha_creacion",
    ]
    ordering = ["nombre"]
    audit_modulo = "configuracion"
    audit_funcionalidad = "entidades institucionales"

    def get_queryset(self):
        queryset = EntidadInstitucional.objects.annotate(
            unidades_count=Count("unidades")
        )
        return filtrar_queryset_por_entidad(queryset, self.request.user, "pk")

    def perform_create(self, serializer):
        if not tiene_alcance_global(self.request.user):
            raise PermissionDenied(
                "Solo un usuario con alcance global puede crear entidades."
            )
        super().perform_create(serializer)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def activar(self, request, pk=None):
        entidad_autorizada = self.get_object()
        entidad = self._obtener_instancia_bloqueada(entidad_autorizada)
        if entidad.estado == EntidadInstitucional.Estado.ACTIVA:
            return Response(
                {"detail": "La entidad ya se encuentra activa."},
                status=status.HTTP_409_CONFLICT,
            )
        antes = serializar_instancia(entidad)
        entidad.estado = EntidadInstitucional.Estado.ACTIVA
        entidad.save(update_fields=["estado", "fecha_actualizacion"])
        registrar_evento(
            request=request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="ACTIVAR",
            instancia=entidad,
            antes=antes,
        )
        return Response(self.get_serializer(entidad).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def desactivar(self, request, pk=None):
        entidad_autorizada = self.get_object()
        entidad = self._obtener_instancia_bloqueada(entidad_autorizada)
        if entidad.estado == EntidadInstitucional.Estado.INACTIVA:
            return Response(
                {"detail": "La entidad ya se encuentra inactiva."},
                status=status.HTTP_409_CONFLICT,
            )
        antes = serializar_instancia(entidad)
        entidad.estado = EntidadInstitucional.Estado.INACTIVA
        entidad.save(update_fields=["estado", "fecha_actualizacion"])
        registrar_evento(
            request=request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="DESACTIVAR",
            instancia=entidad,
            antes=antes,
        )
        return Response(self.get_serializer(entidad).data)


class UnidadOrganizacionalViewSet(
    AuditoriaModelViewSetMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = UnidadOrganizacionalSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "configuracion.ver",
        "retrieve": "configuracion.ver",
        "create": "configuracion.gestionar",
        "update": "configuracion.gestionar",
        "partial_update": "configuracion.gestionar",
        "activar": "configuracion.gestionar",
        "desactivar": "configuracion.gestionar",
    }
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "nombre",
        "codigo",
        "entidad__nombre",
        "entidad__codigo_oficial",
        "unidad_padre__nombre",
    ]
    ordering_fields = [
        "id",
        "nombre",
        "codigo",
        "estado",
        "fecha_creacion",
    ]
    ordering = ["entidad__nombre", "nombre"]
    audit_modulo = "configuracion"
    audit_funcionalidad = "unidades organizacionales"

    def get_queryset(self):
        queryset = (
            UnidadOrganizacional.objects.select_related("entidad", "unidad_padre")
            .annotate(subunidades_count=Count("subunidades"))
        )
        return filtrar_queryset_por_entidad(queryset, self.request.user)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def activar(self, request, pk=None):
        unidad_autorizada = self.get_object()
        unidad = self._obtener_instancia_bloqueada(unidad_autorizada)
        if unidad.estado == UnidadOrganizacional.Estado.ACTIVA:
            return Response(
                {"detail": "La unidad ya se encuentra activa."},
                status=status.HTTP_409_CONFLICT,
            )
        if unidad.entidad.estado != EntidadInstitucional.Estado.ACTIVA:
            return Response(
                {"detail": "No se puede activar una unidad de una entidad inactiva."},
                status=status.HTTP_409_CONFLICT,
            )
        if (
            unidad.unidad_padre_id
            and unidad.unidad_padre.estado != UnidadOrganizacional.Estado.ACTIVA
        ):
            return Response(
                {"detail": "Active primero la unidad superior."},
                status=status.HTTP_409_CONFLICT,
            )
        antes = serializar_instancia(unidad)
        unidad.estado = UnidadOrganizacional.Estado.ACTIVA
        unidad.save(update_fields=["estado", "fecha_actualizacion"])
        registrar_evento(
            request=request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="ACTIVAR",
            instancia=unidad,
            antes=antes,
        )
        return Response(self.get_serializer(unidad).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def desactivar(self, request, pk=None):
        unidad_autorizada = self.get_object()
        unidad = self._obtener_instancia_bloqueada(unidad_autorizada)
        if unidad.estado == UnidadOrganizacional.Estado.INACTIVA:
            return Response(
                {"detail": "La unidad ya se encuentra inactiva."},
                status=status.HTTP_409_CONFLICT,
            )
        if unidad.subunidades.filter(
            estado=UnidadOrganizacional.Estado.ACTIVA
        ).exists():
            return Response(
                {
                    "detail": (
                        "No se puede desactivar una unidad con subunidades activas."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        antes = serializar_instancia(unidad)
        unidad.estado = UnidadOrganizacional.Estado.INACTIVA
        unidad.save(update_fields=["estado", "fecha_actualizacion"])
        registrar_evento(
            request=request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="DESACTIVAR",
            instancia=unidad,
            antes=antes,
        )
        return Response(self.get_serializer(unidad).data)
