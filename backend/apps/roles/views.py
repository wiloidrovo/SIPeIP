from rest_framework import filters, status, viewsets
from django.db.models import Count, IntegerField, Q, Value
from django.db import transaction
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.auditoria.services import (
    AuditoriaModelViewSetMixin,
    registrar_evento,
    serializar_instancia,
)
from apps.configuracion.scope import obtener_alcance_usuario
from .models import Rol
from .permissions import (
    ALLOWED_ROLE_PERMISSIONS,
    BASE_ROLES,
    HasSipeipPermission,
    SCOPE_RESTRICTED_ROLE_CODES,
    alcance_es_delegable,
    es_rol_tecnico_protegido,
)
from .serializers import (
    AsignarPermisosRolSerializer,
    ConfigurarAlcanceRolSerializer,
    RolSerializer,
)


class RolViewSet(AuditoriaModelViewSetMixin, viewsets.ModelViewSet):
    """
    Controlador CRUD para la gestión de roles.
    Expone operaciones de búsqueda, ordenamiento y endpoints personalizados
    para cambio de estado y asignación de permisos.
    """
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "roles.ver",
        "retrieve": "roles.ver",
        "create": "roles.crear",
        "update": "roles.editar",
        "partial_update": "roles.editar",
        "destroy": "roles.eliminar",
        "catalogo_permisos": "roles.asignar_permisos",
        "asignar_permisos": "roles.asignar_permisos",
        "configurar_alcance": "roles.editar",
        "activar": "roles.editar",
        "desactivar": "roles.editar",
    }
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
    audit_modulo = "roles"
    audit_funcionalidad = "roles y permisos"

    def get_queryset(self):
        queryset = super().get_queryset()
        alcance = obtener_alcance_usuario(self.request.user)
        if alcance in {Rol.Alcance.TOTAL, Rol.Alcance.GLOBAL}:
            return queryset.annotate(usuarios_count_anotado=Count("usuarios"))
        entidad_id = getattr(self.request.user, "entidad_id", None)
        if entidad_id:
            return queryset.annotate(
                usuarios_count_anotado=Count(
                    "usuarios",
                    filter=Q(usuarios__entidad_id=entidad_id),
                )
            )
        return queryset.annotate(
            usuarios_count_anotado=Value(0, output_field=IntegerField())
        )

    @staticmethod
    def _proteger_rol_tecnico(actor, rol):
        if es_rol_tecnico_protegido(rol) and not actor.is_superuser:
            raise PermissionDenied(
                "Solo un superusuario puede modificar un rol técnico de acceso total."
            )

    @staticmethod
    def _proteger_alcance(actor, rol):
        if actor.is_superuser:
            return
        if not alcance_es_delegable(
            obtener_alcance_usuario(actor),
            rol.alcance,
        ):
            raise PermissionDenied(
                "No puede modificar un rol con un alcance superior o distinto al propio."
            )

    def perform_create(self, serializer):
        actor = self.request.user
        if not actor.is_superuser and not alcance_es_delegable(
            obtener_alcance_usuario(actor),
            Rol.Alcance.ENTIDAD,
        ):
            raise PermissionDenied(
                "No puede crear roles con un alcance distinto al propio."
            )
        super().perform_create(serializer)

    def perform_update(self, serializer):
        self._proteger_rol_tecnico(self.request.user, serializer.instance)
        self._proteger_alcance(self.request.user, serializer.instance)
        super().perform_update(serializer)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """
        Sobrescribe la eliminación para proteger la integridad referencial.
        No permite eliminar roles que tengan usuarios asignados.
        """
        rol_autorizado = self.get_object()
        rol = Rol.objects.select_for_update().get(pk=rol_autorizado.pk)
        self._proteger_rol_tecnico(request.user, rol)
        self._proteger_alcance(request.user, rol)
        tiene_usuarios = rol.usuarios.exists()

        if tiene_usuarios:
            return Response(
                {
                    "detail": (
                        f"No se puede eliminar el rol '{rol.nombre}' porque "
                        "tiene usuarios asignados. "
                        "Desactive el rol o reasigne los usuarios antes de eliminarlo."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="catalogo-permisos")
    def catalogo_permisos(self, request):
        """Expone los códigos válidos para clientes autorizados de RBAC."""

        return Response(
            {"permisos": list(ALLOWED_ROLE_PERMISSIONS)},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="asignar-permisos")
    @transaction.atomic
    def asignar_permisos(self, request, pk=None):
        """Asigna una lista de permisos al rol validándolos previamente."""
        rol_autorizado = self.get_object()
        rol = Rol.objects.select_for_update().get(pk=rol_autorizado.pk)
        self._proteger_rol_tecnico(request.user, rol)
        self._proteger_alcance(request.user, rol)
        if rol.pk == request.user.rol_id and not request.user.is_superuser:
            raise PermissionDenied("No puede modificar los permisos de su propio rol.")
        entrada = AsignarPermisosRolSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        solicitados = set(entrada.validated_data["permisos"])
        if rol.codigo in SCOPE_RESTRICTED_ROLE_CODES:
            permitidos_por_alcance = set(BASE_ROLES[rol.codigo]["permisos"])
            if not solicitados.issubset(permitidos_por_alcance):
                raise PermissionDenied(
                    "Este rol no puede recibir acceso a datos hasta implementar alcance institucional."
                )
        if not request.user.is_superuser:
            if solicitados >= set(ALLOWED_ROLE_PERMISSIONS):
                raise PermissionDenied(
                    "Solo un superusuario puede configurar acceso técnico total."
                )
            delegables = set(request.user.get_sipeip_permissions())
            if not solicitados.issubset(delegables):
                raise PermissionDenied(
                    "No puede delegar permisos que no posee."
                )
        antes = serializar_instancia(rol)
        rol.permisos = entrada.validated_data["permisos"]
        rol.full_clean()
        rol.save(update_fields=["permisos", "fecha_actualizacion"])
        registrar_evento(
            request=request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="ASIGNAR_PERMISOS",
            instancia=rol,
            antes=antes,
        )

        rol = self.get_queryset().get(pk=rol.pk)
        return Response(self.get_serializer(rol).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="configurar-alcance")
    @transaction.atomic
    def configurar_alcance(self, request, pk=None):
        rol_autorizado = self.get_object()
        rol = Rol.objects.select_for_update().get(pk=rol_autorizado.pk)
        self._proteger_rol_tecnico(request.user, rol)
        self._proteger_alcance(request.user, rol)
        if rol.pk == request.user.rol_id and not request.user.is_superuser:
            raise PermissionDenied(
                "No puede modificar el alcance de su propio rol."
            )
        entrada = ConfigurarAlcanceRolSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        alcance = entrada.validated_data["alcance"]
        alcance_actor = obtener_alcance_usuario(request.user)
        if not request.user.is_superuser:
            if not alcance_es_delegable(alcance_actor, alcance):
                raise PermissionDenied(
                    "No puede otorgar un alcance superior o distinto al propio."
                )
            if alcance_actor not in {Rol.Alcance.TOTAL, Rol.Alcance.GLOBAL}:
                raise PermissionDenied(
                    "Su cuenta no puede modificar alcances institucionales."
                )

        antes = serializar_instancia(rol)
        rol.alcance = alcance
        rol.save(update_fields=["alcance", "fecha_actualizacion"])
        registrar_evento(
            request=request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="CONFIGURAR_ALCANCE",
            instancia=rol,
            antes=antes,
        )
        rol = self.get_queryset().get(pk=rol.pk)
        return Response(self.get_serializer(rol).data)
    
    @action(detail=True, methods=["post"])
    @transaction.atomic
    def activar(self, request, pk=None):
        """Cambia el estado del rol a activo."""
        rol_autorizado = self.get_object()
        rol = Rol.objects.select_for_update().get(pk=rol_autorizado.pk)
        self._proteger_rol_tecnico(request.user, rol)
        self._proteger_alcance(request.user, rol)
        antes = serializar_instancia(rol)
        rol.activo = True
        rol.save(update_fields=["activo", "fecha_actualizacion"])
        registrar_evento(
            request=request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="ACTIVAR",
            instancia=rol,
            antes=antes,
        )

        rol = self.get_queryset().get(pk=rol.pk)
        serializer = self.get_serializer(rol)
        return Response(serializer.data, status=status.HTTP_200_OK)


    @action(detail=True, methods=["post"])
    @transaction.atomic
    def desactivar(self, request, pk=None):
        """Cambia el estado del rol a inactivo."""
        rol_autorizado = self.get_object()
        rol = Rol.objects.select_for_update().get(pk=rol_autorizado.pk)
        self._proteger_rol_tecnico(request.user, rol)
        self._proteger_alcance(request.user, rol)
        antes = serializar_instancia(rol)
        rol.activo = False
        rol.save(update_fields=["activo", "fecha_actualizacion"])
        registrar_evento(
            request=request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="DESACTIVAR",
            instancia=rol,
            antes=antes,
        )

        rol = self.get_queryset().get(pk=rol.pk)
        serializer = self.get_serializer(rol)
        return Response(serializer.data, status=status.HTTP_200_OK)
