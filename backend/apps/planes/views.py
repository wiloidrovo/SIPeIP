from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Plan
from .serializers import PlanSerializer


class PlanViewSet(viewsets.ModelViewSet):
    """
    API REST para la gestión de planes institucionales.

    Permite registrar, consultar, editar y eliminar planes. Además expone una
    acción específica para enviar un plan a revisión, representando un primer
    flujo de negocio dentro del módulo.
    """

    queryset = Plan.objects.select_related("responsable").all()
    serializer_class = PlanSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "nombre",
        "descripcion",
        "estado",
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

    def destroy(self, request, *args, **kwargs):
        """
        Restringe la eliminación de planes que ya ingresaron a revisión.

        Esta regla protege la trazabilidad del proceso. Los planes en borrador,
        rechazados o archivados pueden eliminarse; los planes en revisión o
        aprobados deben conservarse como evidencia del flujo institucional.
        """

        plan = self.get_object()

        if plan.estado in [Plan.EstadoPlan.EN_REVISION, Plan.EstadoPlan.APROBADO]:
            return Response(
                {
                    "detail": (
                        "No se puede eliminar un plan que se encuentra "
                        "en revisión o aprobado. Archive el registro si "
                        "ya no debe mantenerse activo."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="enviar-a-revision")
    def enviar_a_revision(self, request, pk=None):
        """
        Cambia el estado de un plan desde borrador o rechazado hacia revisión.
        """

        plan = self.get_object()

        if plan.estado not in [Plan.EstadoPlan.BORRADOR, Plan.EstadoPlan.RECHAZADO]:
            return Response(
                {
                    "detail": (
                        "Solo los planes en estado borrador o rechazado "
                        "pueden enviarse a revisión."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        plan.estado = Plan.EstadoPlan.EN_REVISION
        plan.save(update_fields=["estado", "fecha_actualizacion"])

        serializer = self.get_serializer(plan)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def archivar(self, request, pk=None):
        """
        Archiva un plan sin eliminarlo físicamente de la base de datos.
        """

        plan = self.get_object()
        plan.estado = Plan.EstadoPlan.ARCHIVADO
        plan.activo = False
        plan.save(update_fields=["estado", "activo", "fecha_actualizacion"])

        serializer = self.get_serializer(plan)
        return Response(serializer.data, status=status.HTTP_200_OK)