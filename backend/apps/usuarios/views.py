from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Usuario
from .serializers import UsuarioSerializer


class UsuarioViewSet(viewsets.ModelViewSet):
    """
    Controlador CRUD para la gestión de usuarios.
    Permite el manejo de información del usuario y acciones directas para 
    el control de estado de acceso (activar, bloquear).
    """
    # Se utiliza select_related('rol') para evitar el problema de N+1 queries.
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

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        """Cambia el estado del usuario a activo y permite el inicio de sesión."""
        usuario = self.get_object()
        usuario.estado = Usuario.EstadoUsuario.ACTIVO
        usuario.is_active = True
        usuario.save(update_fields=["estado", "is_active"])

        serializer = self.get_serializer(usuario)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def bloquear(self, request, pk=None):
        """Cambia el estado a bloqueado e impide futuros inicios de sesión."""
        usuario = self.get_object()
        usuario.estado = Usuario.EstadoUsuario.BLOQUEADO
        usuario.is_active = False
        usuario.save(update_fields=["estado", "is_active"])

        serializer = self.get_serializer(usuario)
        return Response(serializer.data, status=status.HTTP_200_OK)