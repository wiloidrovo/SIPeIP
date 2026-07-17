from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models.deletion import ProtectedError
from django.db import IntegrityError, transaction

from apps.auditoria.services import (
    AuditoriaModelViewSetMixin,
    registrar_evento,
    serializar_instancia,
)
from apps.configuracion.scope import filtrar_queryset_por_entidad
from apps.roles.permissions import HasSipeipPermission, es_rol_tecnico_protegido

from .models import Usuario
from .serializers import UsuarioSerializer


class UsuarioViewSet(AuditoriaModelViewSetMixin, viewsets.ModelViewSet):
    """
    Controlador CRUD para la gestión de usuarios.
    Permite el manejo de información del usuario y acciones directas para 
    el control de estado de acceso (activar, bloquear).
    """
    # Se utiliza select_related('rol') para evitar el problema de N+1 queries.
    queryset = Usuario.objects.select_related(
        "rol", "entidad", "unidad_organizacional"
    ).all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "usuarios.ver",
        "retrieve": "usuarios.ver",
        "create": "usuarios.crear",
        "update": "usuarios.editar",
        "partial_update": "usuarios.editar",
        "destroy": "usuarios.eliminar",
        "activar": "usuarios.editar",
        "bloquear": "usuarios.editar",
    }
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
    audit_modulo = "usuarios"
    audit_funcionalidad = "usuarios"

    def get_queryset(self):
        return filtrar_queryset_por_entidad(
            super().get_queryset(), self.request.user, "entidad"
        )

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {
                    "detail": (
                        "No se puede crear el usuario porque el nombre o el "
                        "correo ya están registrados."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

    @staticmethod
    def _tiene_registros_trazables(usuario):
        relaciones = (
            "planes_responsables",
            "planes_creados",
            "transiciones_planes",
            "proyectos_inversion_responsables",
            "proyectos_inversion_creados",
            "seguimientos_proyectos",
            "alineaciones_creadas",
            "alineaciones_validadas",
            "indicadores_validados",
            "avances_indicadores",
            "eventos_auditoria",
        )
        return any(getattr(usuario, relacion).exists() for relacion in relaciones)

    @staticmethod
    def _proteger_cuenta_administrativa(actor, objetivo):
        es_administrativa = (
            objetivo.is_staff
            or objetivo.is_superuser
            or es_rol_tecnico_protegido(objetivo.rol)
        )
        if es_administrativa and not actor.is_superuser:
            raise PermissionDenied(
                "Solo un superusuario puede modificar una cuenta administrativa."
            )

    def update(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                return self._actualizar_bloqueado(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {
                    "detail": (
                        "No se puede actualizar el usuario porque el nombre o "
                        "el correo ya están registrados."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

    def _actualizar_bloqueado(self, request, *args, **kwargs):
        usuario_autorizado = self.get_object()
        usuario = self._obtener_instancia_bloqueada(usuario_autorizado)
        self._proteger_cuenta_administrativa(request.user, usuario)

        if "entidad" in request.data:
            entidad_solicitada = request.data.get("entidad")
            entidad_actual = str(usuario.entidad_id) if usuario.entidad_id else None
            entidad_nueva = (
                str(entidad_solicitada)
                if entidad_solicitada not in (None, "")
                else None
            )
            if (
                entidad_actual != entidad_nueva
                and self._tiene_registros_trazables(usuario)
            ):
                return Response(
                    {
                        "detail": (
                            "No se puede cambiar la entidad de un usuario con "
                            "registros institucionales o trazables. Reasigne los "
                            "registros mediante un flujo administrativo controlado."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """
        Evita eliminar usuarios que todavía están vinculados a planes.

        La relación Plan.responsable usa PROTECT para preservar la trazabilidad
        institucional. Si un usuario tiene planes asignados, debe bloquearse o
        reasignarse antes de permitir su eliminación física.
        """

        usuario_autorizado = self.get_object()
        usuario = self._obtener_instancia_bloqueada(usuario_autorizado)
        if usuario.pk == request.user.pk:
            raise PermissionDenied("No puede eliminar su propia cuenta.")
        self._proteger_cuenta_administrativa(request.user, usuario)
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
    @transaction.atomic
    def activar(self, request, pk=None):
        """Cambia el estado del usuario a activo y permite el inicio de sesión."""
        usuario_autorizado = self.get_object()
        usuario = self._obtener_instancia_bloqueada(usuario_autorizado)
        self._proteger_cuenta_administrativa(request.user, usuario)
        antes = serializar_instancia(usuario)
        usuario.estado = Usuario.EstadoUsuario.ACTIVO
        usuario.is_active = True
        usuario.save(update_fields=["estado", "is_active"])
        registrar_evento(
            request=request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="ACTIVAR",
            instancia=usuario,
            antes=antes,
        )

        serializer = self.get_serializer(usuario)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def bloquear(self, request, pk=None):
        """Cambia el estado a bloqueado e impide futuros inicios de sesión."""
        usuario_autorizado = self.get_object()
        usuario = self._obtener_instancia_bloqueada(usuario_autorizado)
        self._proteger_cuenta_administrativa(request.user, usuario)
        antes = serializar_instancia(usuario)
        usuario.estado = Usuario.EstadoUsuario.BLOQUEADO
        usuario.is_active = False
        usuario.save(update_fields=["estado", "is_active"])
        registrar_evento(
            request=request,
            modulo=self.audit_modulo,
            funcionalidad=self.audit_funcionalidad,
            accion="BLOQUEAR",
            instancia=usuario,
            antes=antes,
        )

        serializer = self.get_serializer(usuario)
        return Response(serializer.data, status=status.HTTP_200_OK)
