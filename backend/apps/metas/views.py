from django.db.models.deletion import ProtectedError
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import AvanceIndicador, Indicador, Meta
from .serializers import (
    AvanceIndicadorSerializer,
    IndicadorSerializer,
    MetaSerializer,
)


class MetaViewSet(viewsets.ModelViewSet):
    """
    API REST para gestionar metas institucionales asociadas a planes.
    """

    queryset = Meta.objects.select_related("plan").all()
    serializer_class = MetaSerializer
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

    def destroy(self, request, *args, **kwargs):
        """
        Evita eliminar metas que ya tienen indicadores asociados.
        """

        meta = self.get_object()
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

    @action(detail=True, methods=["post"])
    def archivar(self, request, pk=None):
        """
        Archiva una meta sin eliminarla físicamente.
        """

        meta = self.get_object()
        meta.estado = Meta.EstadoMeta.ARCHIVADA
        meta.activa = False
        meta.save(update_fields=["estado", "activa", "fecha_actualizacion"])

        serializer = self.get_serializer(meta)
        return Response(serializer.data, status=status.HTTP_200_OK)


class IndicadorViewSet(viewsets.ModelViewSet):
    """
    API REST para gestionar indicadores y registrar avances de medición.
    """

    queryset = Indicador.objects.select_related("meta", "meta__plan").all()
    serializer_class = IndicadorSerializer
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

    def destroy(self, request, *args, **kwargs):
        """
        Evita eliminar indicadores que ya tienen avances registrados.
        """

        indicador = self.get_object()
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

        indicador = self.get_object()
        data = request.data.copy()
        data["indicador"] = indicador.id

        serializer = AvanceIndicadorSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        avance = serializer.save()

        indicador.valor_actual = avance.valor
        indicador.save(update_fields=["valor_actual", "fecha_actualizacion"])

        response_serializer = AvanceIndicadorSerializer(avance)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        """
        Activa un indicador para permitir nuevos registros de avance.
        """

        indicador = self.get_object()
        indicador.activo = True
        indicador.save(update_fields=["activo", "fecha_actualizacion"])

        serializer = self.get_serializer(indicador)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        """
        Desactiva un indicador sin eliminar sus avances históricos.
        """

        indicador = self.get_object()
        indicador.activo = False
        indicador.save(update_fields=["activo", "fecha_actualizacion"])

        serializer = self.get_serializer(indicador)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "indicador__nombre",
        "indicador__meta__nombre",
        "observacion",
    ]
    ordering_fields = ["id", "fecha_registro", "valor", "fecha_creacion"]
    ordering = ["-fecha_registro", "-fecha_creacion"]