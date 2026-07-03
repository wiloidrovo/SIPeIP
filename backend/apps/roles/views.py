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

    def destroy(self, request, *args, **kwargs):
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
        rol = self.get_object()
        rol.activo = True
        rol.save(update_fields=["activo", "fecha_actualizacion"])

        serializer = self.get_serializer(rol)
        return Response(serializer.data, status=status.HTTP_200_OK)


    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        rol = self.get_object()
        rol.activo = False
        rol.save(update_fields=["activo", "fecha_actualizacion"])

        serializer = self.get_serializer(rol)
        return Response(serializer.data, status=status.HTTP_200_OK)