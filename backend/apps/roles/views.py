from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Rol
from .serializers import RolSerializer


class RolViewSet(viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = [
        "nombre",
        "descripcion",
    ]
    ordering_fields = [
        "id",
        "nombre",
        "activo",
        "fecha_creacion",
    ]
    ordering = [
        "nombre",
    ]

    @action(detail=True, methods=["post"], url_path="asignar-permisos")
    def asignar_permisos(self, request, pk=None):
        rol = self.get_object()
        permisos = request.data.get("permisos", [])

        if not isinstance(permisos, list):
            return Response(
                {"detail": "El campo permisos debe ser una lista."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rol.permisos = permisos
        rol.save(update_fields=["permisos", "fecha_actualizacion"])

        serializer = self.get_serializer(rol)
        return Response(serializer.data, status=status.HTTP_200_OK)