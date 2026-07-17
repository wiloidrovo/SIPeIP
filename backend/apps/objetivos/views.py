from django.db import transaction
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
from apps.configuracion.scope import filtrar_queryset_por_entidad
from apps.roles.permissions import HasSipeipPermission

from .models import Alineacion, EjePND, EstadoCatalogo, ObjetivoEstrategico, ObjetivoPND, ODS
from .serializers import (
    AlineacionSerializer,
    EjePNDSerializer,
    ObjetivoEstrategicoSerializer,
    ObjetivoPNDSerializer,
    ODSSerializer,
)


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
    EliminacionProtegidaMixin,
    AccionesEstadoCatalogoMixin,
    AuditoriaModelViewSetMixin,
    viewsets.ModelViewSet,
):
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
        queryset = ObjetivoEstrategico.objects.select_related("entidad")
        queryset = filtrar_queryset_por_entidad(
            queryset,
            self.request.user,
            "entidad",
        )
        entidad = self.request.query_params.get("entidad")
        estado_filtro = self.request.query_params.get("estado")
        if entidad and entidad.isdigit():
            queryset = queryset.filter(entidad_id=int(entidad))
        if estado_filtro in EstadoCatalogo.values:
            queryset = queryset.filter(estado=estado_filtro)
        return queryset


class EjePNDViewSet(
    EliminacionProtegidaMixin,
    AccionesEstadoCatalogoMixin,
    AuditoriaModelViewSetMixin,
    viewsets.ModelViewSet,
):
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
    EliminacionProtegidaMixin,
    AccionesEstadoCatalogoMixin,
    AuditoriaModelViewSetMixin,
    viewsets.ModelViewSet,
):
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
    EliminacionProtegidaMixin,
    AccionesEstadoCatalogoMixin,
    AuditoriaModelViewSetMixin,
    viewsets.ModelViewSet,
):
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

    def get_queryset(self):
        queryset = Alineacion.objects.select_related(
            "objetivo_estrategico__entidad",
            "objetivo_pnd__eje",
            "ods",
            "usuario_creador",
            "usuario_validador",
        )
        queryset = filtrar_queryset_por_entidad(
            queryset,
            self.request.user,
            "objetivo_estrategico__entidad",
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
            alineacion = self._obtener_bloqueada()
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
