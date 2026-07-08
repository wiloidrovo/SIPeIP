from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models.deletion import ProtectedError
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

    def destroy(self, request, *args, **kwargs):
        """
        Evita eliminar usuarios que todavía están vinculados a planes.

        La relación Plan.responsable usa PROTECT para preservar la trazabilidad
        institucional. Si un usuario tiene planes asignados, debe bloquearse o
        reasignarse antes de permitir su eliminación física.
        """

        usuario = self.get_object()
        planes_count = usuario.planes_responsables.count()

        if planes_count > 0:
            return Response(
                {
                    "detail": (
                        f"No se puede eliminar el usuario '{usuario.username}' "
                        f"porque está asignado como responsable de {planes_count} "
                        "plan(es). Reasigne esos planes o bloquee el usuario "
                        "antes de eliminarlo."
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
                        "No se puede eliminar este usuario porque está vinculado "
                        "a otros registros del sistema. Reasigne o archive esos "
                        "registros antes de eliminarlo."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

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