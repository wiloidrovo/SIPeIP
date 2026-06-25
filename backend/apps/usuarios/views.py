from rest_framework import filters, viewsets

from .models import Usuario
from .serializers import UsuarioSerializer


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.select_related("rol").all()
    serializer_class = UsuarioSerializer
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = [
        "username",
        "email",
        "first_name",
        "last_name",
        "estado",
    ]
    ordering_fields = [
        "id",
        "username",
        "email",
        "estado",
        "date_joined",
    ]
    ordering = [
        "username",
    ]