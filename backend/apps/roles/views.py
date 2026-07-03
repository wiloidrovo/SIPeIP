from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Rol
from .serializers import RolSerializer


class RolViewSet(viewsets.ModelViewSet):
    """
    Controlador CRUD para la gestión de roles.
    Expone operaciones de búsqueda, ordenamiento y endpoints personalizados
    para cambio de estado y asignación de permisos.
    """
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

    def destroy(self, request, *args, **kwargs):
        """
        Sobrescribe la eliminación para proteger la integridad referencial.
        No permite eliminar roles que tengan usuarios asignados.
        """
        rol = self.get_object()
        usuarios_count = rol.usuarios.count()

        if usuarios_count > 0:
            return Response(
                {
                    "detail": (
                        f"No se puede eliminar el rol '{rol.nombre}' porque "
                        f"está asignado a {usuarios_count} usuario(s). "
                        "Desactive el rol o reasigne los usuarios antes de eliminarlo."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="asignar-permisos")
    def asignar_permisos(self, request, pk=None):
        """Asigna una lista de permisos al rol validándolos previamente."""
        rol = self.get_object()
        permisos = request.data.get("permisos", [])

        serializer = self.get_serializer(
            rol,
            data={"permisos": permisos},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        """Cambia el estado del rol a activo."""
        rol = self.get_object()
        rol.activo = True
        rol.save(update_fields=["activo", "fecha_actualizacion"])

        serializer = self.get_serializer(rol)
        return Response(serializer.data, status=status.HTTP_200_OK)


    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        """Cambia el estado del rol a inactivo."""
        rol = self.get_object()
        rol.activo = False
        rol.save(update_fields=["activo", "fecha_actualizacion"])

        serializer = self.get_serializer(rol)
        return Response(serializer.data, status=status.HTTP_200_OK)