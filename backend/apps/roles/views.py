from rest_framework import filters, viewsets

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