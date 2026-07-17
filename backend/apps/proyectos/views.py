from django.db import IntegrityError, transaction
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.auditoria.services import registrar_evento, serializar_instancia
from apps.roles.permissions import HasSipeipPermission

from .models import (
    HitoProyecto,
    ProyectoInversion,
    SeguimientoProyecto,
    TipologiaIntervencion,
)
from .serializers import (
    DevolucionProyectoSerializer,
    HitoProyectoSerializer,
    ProyectoInversionSerializer,
    SeguimientoProyectoSerializer,
    TipologiaIntervencionSerializer,
)
from .scope import filtrar_proyectos_por_alcance, proyecto_esta_en_alcance


ESTADOS_EDITABLES = {
    ProyectoInversion.EstadoProyecto.BORRADOR,
    ProyectoInversion.EstadoProyecto.PLANIFICADO,
}
class TipologiaIntervencionViewSet(viewsets.ModelViewSet):
    """Catálogo global configurable, protegido por permisos explícitos."""

    serializer_class = TipologiaIntervencionSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "proyectos.ver",
        "retrieve": "proyectos.ver",
        "create": "proyectos.gestionar_catalogos",
        "update": "proyectos.gestionar_catalogos",
        "partial_update": "proyectos.gestionar_catalogos",
        "destroy": "proyectos.gestionar_catalogos",
        "activar": "proyectos.gestionar_catalogos",
        "desactivar": "proyectos.gestionar_catalogos",
    }
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["codigo", "nombre", "descripcion"]
    ordering_fields = [
        "id",
        "codigo",
        "nombre",
        "activo",
        "fecha_creacion",
    ]
    ordering = ["nombre", "codigo"]

    def get_queryset(self):
        # Catálogo de referencia global: no pertenece a una institución.
        return TipologiaIntervencion.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                tipologia = serializer.save()
                registrar_evento(
                    request=request,
                    modulo="proyectos",
                    funcionalidad="catálogo de tipologías de intervención",
                    accion="CREAR",
                    instancia=tipologia,
                )
        except IntegrityError:
            return Response(
                {"detail": "Ya existe una tipología con ese código o nombre."},
                status=status.HTTP_409_CONFLICT,
            )
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def update(self, request, *args, **kwargs):
        parcial = kwargs.pop("partial", False)
        tipologia_autorizada = self.get_object()
        try:
            with transaction.atomic():
                tipologia = TipologiaIntervencion.objects.select_for_update().get(
                    pk=tipologia_autorizada.pk
                )
                serializer = self.get_serializer(
                    tipologia,
                    data=request.data,
                    partial=parcial,
                )
                serializer.is_valid(raise_exception=True)
                antes = serializar_instancia(tipologia)
                tipologia = serializer.save()
                registrar_evento(
                    request=request,
                    modulo="proyectos",
                    funcionalidad="catálogo de tipologías de intervención",
                    accion="EDITAR",
                    instancia=tipologia,
                    antes=antes,
                )
        except IntegrityError:
            return Response(
                {"detail": "Ya existe una tipología con ese código o nombre."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        tipologia_autorizada = self.get_object()
        try:
            with transaction.atomic():
                tipologia = TipologiaIntervencion.objects.select_for_update().get(
                    pk=tipologia_autorizada.pk
                )
                antes = serializar_instancia(tipologia)
                registrar_evento(
                    request=request,
                    modulo="proyectos",
                    funcionalidad="catálogo de tipologías de intervención",
                    accion="ELIMINAR",
                    instancia=tipologia,
                    antes=antes,
                    despues={},
                )
                tipologia.delete()
        except ProtectedError:
            return Response(
                {
                    "detail": (
                        "No se puede eliminar la tipología porque está vinculada "
                        "con uno o más proyectos. Puede desactivarla."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _cambiar_estado(self, tipologia_autorizada, activo, accion):
        with transaction.atomic():
            tipologia = TipologiaIntervencion.objects.select_for_update().get(
                pk=tipologia_autorizada.pk
            )
            if tipologia.activo == activo:
                estado_actual = "activa" if activo else "inactiva"
                return Response(
                    {"detail": f"La tipología ya se encuentra {estado_actual}."},
                    status=status.HTTP_409_CONFLICT,
                )
            antes = serializar_instancia(tipologia)
            tipologia.activo = activo
            tipologia.save(update_fields=["activo", "fecha_actualizacion"])
            registrar_evento(
                request=self.request,
                modulo="proyectos",
                funcionalidad="catálogo de tipologías de intervención",
                accion=accion,
                instancia=tipologia,
                antes=antes,
            )
        return Response(self.get_serializer(tipologia).data)

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        return self._cambiar_estado(self.get_object(), True, "ACTIVAR")

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        return self._cambiar_estado(self.get_object(), False, "DESACTIVAR")


class ProyectoInversionViewSet(viewsets.ModelViewSet):
    serializer_class = ProyectoInversionSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "proyectos.ver",
        "retrieve": "proyectos.ver",
        "create": "proyectos.crear",
        "update": "proyectos.editar",
        "partial_update": "proyectos.editar",
        "destroy": "proyectos.eliminar",
        "planificar": "proyectos.editar",
        "enviar_a_revision": "proyectos.enviar_revision",
        "devolver": "proyectos.devolver",
        "aprobar": "proyectos.aprobar",
        "iniciar_ejecucion": "proyectos.editar",
        "suspender": "proyectos.editar",
        "reanudar": "proyectos.editar",
        "finalizar": "proyectos.editar",
        "archivar": "proyectos.archivar",
        "registrar_seguimiento": "proyectos.registrar_seguimiento",
    }
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "codigo",
        "nombre",
        "descripcion",
        "tipologia_intervencion__codigo",
        "tipologia_intervencion__nombre",
        "estado",
        "entidad__codigo_oficial",
        "entidad__nombre",
        "plan__nombre",
        "objetivo_estrategico__codigo",
        "objetivo_estrategico__nombre",
        "responsable__username",
        "responsable__first_name",
        "responsable__last_name",
    ]
    ordering_fields = [
        "id",
        "codigo",
        "nombre",
        "estado",
        "fecha_inicio",
        "fecha_fin",
        "presupuesto_estimado",
        "avance_fisico",
        "avance_financiero",
        "fecha_creacion",
    ]
    ordering = ["-fecha_creacion", "codigo"]

    def get_queryset(self):
        queryset = (
            ProyectoInversion.objects.select_related(
                "entidad",
                "plan",
                "objetivo_estrategico",
                "tipologia_intervencion",
                "responsable",
                "creado_por",
            )
            .annotate(
                hitos_total=Count("hitos", distinct=True),
                seguimientos_total=Count("seguimientos", distinct=True),
            )
            .all()
        )
        return filtrar_proyectos_por_alcance(queryset, self.request.user)

    def perform_create(self, serializer):
        proyecto = serializer.save(creado_por=self.request.user)
        registrar_evento(
            request=self.request,
            modulo="proyectos",
            funcionalidad="proyectos de inversión",
            accion="CREAR",
            instancia=proyecto,
            entidad=proyecto.entidad,
        )

    def perform_update(self, serializer):
        antes = serializar_instancia(serializer.instance)
        proyecto = serializer.save()
        registrar_evento(
            request=self.request,
            modulo="proyectos",
            funcionalidad="proyectos de inversión",
            accion="EDITAR",
            instancia=proyecto,
            antes=antes,
            entidad=proyecto.entidad,
        )

    def _bloquear_y_revalidar_relaciones(self, serializer):
        datos = dict(serializer.validated_data)
        for campo in (
            "entidad",
            "plan",
            "objetivo_estrategico",
            "tipologia_intervencion",
            "responsable",
        ):
            objeto = datos.get(
                campo,
                getattr(serializer.instance, campo, None)
                if serializer.instance is not None
                else None,
            )
            if objeto is None:
                continue
            datos[campo] = (
                objeto.__class__._default_manager.select_for_update().get(
                    pk=objeto.pk
                )
            )
        serializer._validated_data = serializer.validate(datos)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                self._bloquear_y_revalidar_relaciones(serializer)
                self.perform_create(serializer)
        except IntegrityError:
            return Response(
                {"detail": "Ya existe un proyecto con ese código en la entidad."},
                status=status.HTTP_409_CONFLICT,
            )
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def update(self, request, *args, **kwargs):
        parcial = kwargs.pop("partial", False)
        proyecto_autorizado = self.get_object()
        try:
            with transaction.atomic():
                proyecto = self._obtener_bloqueado(proyecto_autorizado)
                serializer = self.get_serializer(
                    proyecto,
                    data=request.data,
                    partial=parcial,
                )
                serializer.is_valid(raise_exception=True)
                self._bloquear_y_revalidar_relaciones(serializer)
                self.perform_update(serializer)
        except IntegrityError:
            return Response(
                {"detail": "Ya existe un proyecto con ese código en la entidad."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        proyecto_autorizado = self.get_object()
        try:
            with transaction.atomic():
                proyecto = self._obtener_bloqueado(proyecto_autorizado)
                if proyecto.estado != ProyectoInversion.EstadoProyecto.BORRADOR:
                    return Response(
                        {
                            "detail": (
                                "Solo se puede eliminar físicamente un proyecto en "
                                "borrador. Use archivo para conservar la trazabilidad."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )
                if proyecto.hitos.exists() or proyecto.seguimientos.exists():
                    return Response(
                        {
                            "detail": (
                                "No se puede eliminar el proyecto porque tiene hitos o "
                                "seguimientos vinculados."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )
                antes = serializar_instancia(proyecto)
                registrar_evento(
                    request=request,
                    modulo="proyectos",
                    funcionalidad="proyectos de inversión",
                    accion="ELIMINAR",
                    instancia=proyecto,
                    antes=antes,
                    despues={},
                    entidad=proyecto.entidad,
                )
                proyecto.delete()
        except ProtectedError:
            return Response(
                {
                    "detail": (
                        "No se puede eliminar el proyecto porque mantiene "
                        "relaciones protegidas."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _obtener_bloqueado(self, proyecto_autorizado):
        proyecto = (
            ProyectoInversion.objects.select_for_update()
            .select_related(
                "entidad",
                "plan",
                "objetivo_estrategico",
                "tipologia_intervencion",
                "creado_por",
            )
            .get(pk=proyecto_autorizado.pk)
        )
        if not proyecto_esta_en_alcance(proyecto, self.request.user):
            raise NotFound("No se encontró el proyecto solicitado.")
        return proyecto

    def _transicionar(
        self,
        proyecto_autorizado,
        estados_origen,
        nuevo_estado,
        accion,
        *,
        detalle="",
    ):
        with transaction.atomic():
            proyecto = self._obtener_bloqueado(proyecto_autorizado)
            if proyecto.estado not in estados_origen:
                permitidos = ", ".join(sorted(estados_origen))
                return Response(
                    {
                        "detail": (
                            f"La acción '{accion}' solo está permitida desde: "
                            f"{permitidos}."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            antes = serializar_instancia(proyecto)
            proyecto.estado = nuevo_estado
            proyecto.activo = nuevo_estado != ProyectoInversion.EstadoProyecto.ARCHIVADO
            proyecto.save(update_fields=["estado", "activo", "fecha_actualizacion"])
            registrar_evento(
                request=self.request,
                modulo="proyectos",
                funcionalidad="flujo de proyectos",
                accion=accion.upper(),
                instancia=proyecto,
                antes=antes,
                entidad=proyecto.entidad,
                detalle=detalle,
            )

        return Response(self.get_serializer(proyecto).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def planificar(self, request, pk=None):
        return self._transicionar(
            self.get_object(),
            {ProyectoInversion.EstadoProyecto.BORRADOR},
            ProyectoInversion.EstadoProyecto.PLANIFICADO,
            "planificar",
        )

    @action(detail=True, methods=["post"], url_path="enviar-a-revision")
    def enviar_a_revision(self, request, pk=None):
        return self._transicionar(
            self.get_object(),
            {ProyectoInversion.EstadoProyecto.PLANIFICADO},
            ProyectoInversion.EstadoProyecto.EN_REVISION,
            "enviar_a_revision",
        )

    @action(detail=True, methods=["post"])
    def devolver(self, request, pk=None):
        entrada = DevolucionProyectoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        return self._transicionar(
            self.get_object(),
            {ProyectoInversion.EstadoProyecto.EN_REVISION},
            ProyectoInversion.EstadoProyecto.PLANIFICADO,
            "devolver",
            detalle=entrada.validated_data["observacion"],
        )

    @action(detail=True, methods=["post"])
    def aprobar(self, request, pk=None):
        return self._transicionar(
            self.get_object(),
            {ProyectoInversion.EstadoProyecto.EN_REVISION},
            ProyectoInversion.EstadoProyecto.APROBADO,
            "aprobar",
        )

    @action(detail=True, methods=["post"], url_path="iniciar-ejecucion")
    def iniciar_ejecucion(self, request, pk=None):
        return self._transicionar(
            self.get_object(),
            {ProyectoInversion.EstadoProyecto.APROBADO},
            ProyectoInversion.EstadoProyecto.EN_EJECUCION,
            "iniciar_ejecucion",
        )

    @action(detail=True, methods=["post"])
    def suspender(self, request, pk=None):
        return self._transicionar(
            self.get_object(),
            {ProyectoInversion.EstadoProyecto.EN_EJECUCION},
            ProyectoInversion.EstadoProyecto.SUSPENDIDO,
            "suspender",
        )

    @action(detail=True, methods=["post"])
    def reanudar(self, request, pk=None):
        return self._transicionar(
            self.get_object(),
            {ProyectoInversion.EstadoProyecto.SUSPENDIDO},
            ProyectoInversion.EstadoProyecto.EN_EJECUCION,
            "reanudar",
        )

    @action(detail=True, methods=["post"])
    def finalizar(self, request, pk=None):
        return self._transicionar(
            self.get_object(),
            {ProyectoInversion.EstadoProyecto.EN_EJECUCION},
            ProyectoInversion.EstadoProyecto.FINALIZADO,
            "finalizar",
        )

    @action(detail=True, methods=["post"])
    def archivar(self, request, pk=None):
        return self._transicionar(
            self.get_object(),
            {
                ProyectoInversion.EstadoProyecto.BORRADOR,
                ProyectoInversion.EstadoProyecto.PLANIFICADO,
                ProyectoInversion.EstadoProyecto.APROBADO,
                ProyectoInversion.EstadoProyecto.SUSPENDIDO,
                ProyectoInversion.EstadoProyecto.FINALIZADO,
            },
            ProyectoInversion.EstadoProyecto.ARCHIVADO,
            "archivar",
        )

    @action(detail=True, methods=["post"], url_path="registrar-seguimiento")
    def registrar_seguimiento(self, request, pk=None):
        proyecto_autorizado = self.get_object()

        with transaction.atomic():
            proyecto = self._obtener_bloqueado(proyecto_autorizado)
            contexto = self.get_serializer_context()
            contexto["proyecto"] = proyecto
            serializer = SeguimientoProyectoSerializer(
                data=request.data,
                context=contexto,
            )
            serializer.is_valid(raise_exception=True)
            ultimo_previo = proyecto.seguimientos.order_by(
                "-fecha_registro",
                "-fecha_creacion",
            ).first()
            seguimiento = serializer.save(
                proyecto=proyecto,
                registrado_por=request.user,
            )

            es_corte_mas_reciente = (
                ultimo_previo is None
                or seguimiento.fecha_registro > ultimo_previo.fecha_registro
            )
            antes = None
            if es_corte_mas_reciente:
                antes = serializar_instancia(proyecto)
                proyecto.avance_fisico = seguimiento.avance_fisico
                proyecto.avance_financiero = seguimiento.avance_financiero
                proyecto.save(
                    update_fields=[
                        "avance_fisico",
                        "avance_financiero",
                        "fecha_actualizacion",
                    ]
                )
            registrar_evento(
                request=request,
                modulo="proyectos",
                funcionalidad="seguimiento de proyectos",
                accion="REGISTRAR_SEGUIMIENTO",
                instancia=seguimiento,
                antes={},
                entidad=proyecto.entidad,
                detalle=(
                    f"Avance físico {seguimiento.avance_fisico}% y "
                    f"financiero {seguimiento.avance_financiero}%. "
                    + (
                        "Actualizó el avance consolidado."
                        if es_corte_mas_reciente
                        else "Corte histórico; no alteró el avance consolidado."
                    )
                ),
            )
            if es_corte_mas_reciente:
                registrar_evento(
                    request=request,
                    modulo="proyectos",
                    funcionalidad="avance consolidado",
                    accion="ACTUALIZAR_AVANCE",
                    instancia=proyecto,
                    antes=antes,
                    entidad=proyecto.entidad,
                )

        return Response(
            SeguimientoProyectoSerializer(
                seguimiento,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_201_CREATED,
        )


class HitoProyectoViewSet(viewsets.ModelViewSet):
    serializer_class = HitoProyectoSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "proyectos.ver",
        "retrieve": "proyectos.ver",
        "create": "proyectos.editar",
        "update": "proyectos.editar",
        "partial_update": "proyectos.editar",
        "destroy": "proyectos.editar",
    }
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nombre", "descripcion", "proyecto__codigo", "proyecto__nombre"]
    ordering_fields = ["id", "proyecto", "orden", "fecha_inicio_planificada"]
    ordering = ["proyecto", "orden"]

    def get_queryset(self):
        proyectos = filtrar_proyectos_por_alcance(
            ProyectoInversion.objects.all(),
            self.request.user,
        )
        return HitoProyecto.objects.select_related(
            "proyecto",
            "proyecto__entidad",
        ).filter(proyecto__in=proyectos)

    def _bloquear_proyecto(self, proyecto_id):
        proyecto = (
            ProyectoInversion.objects.select_for_update()
            .select_related("entidad")
            .get(pk=proyecto_id)
        )
        if not proyecto_esta_en_alcance(proyecto, self.request.user):
            raise NotFound("No se encontró el proyecto solicitado.")
        return proyecto

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proyecto_validado = serializer.validated_data["proyecto"]
        try:
            with transaction.atomic():
                proyecto = self._bloquear_proyecto(proyecto_validado.pk)
                datos = dict(serializer.validated_data)
                datos["proyecto"] = proyecto
                serializer._validated_data = serializer.validate(datos)
                hito = serializer.save()
                registrar_evento(
                    request=request,
                    modulo="proyectos",
                    funcionalidad="hitos",
                    accion="CREAR",
                    instancia=hito,
                    entidad=proyecto.entidad,
                )
        except IntegrityError:
            return Response(
                {"detail": "Ya existe un hito con ese orden o nombre."},
                status=status.HTTP_409_CONFLICT,
            )
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def update(self, request, *args, **kwargs):
        parcial = kwargs.pop("partial", False)
        hito_autorizado = self.get_object()
        try:
            with transaction.atomic():
                proyecto = self._bloquear_proyecto(hito_autorizado.proyecto_id)
                hito = (
                    HitoProyecto.objects.select_for_update()
                    .select_related("proyecto", "proyecto__entidad")
                    .get(pk=hito_autorizado.pk, proyecto_id=proyecto.pk)
                )
                serializer = self.get_serializer(
                    hito,
                    data=request.data,
                    partial=parcial,
                )
                serializer.is_valid(raise_exception=True)
                antes = serializar_instancia(hito)
                hito = serializer.save()
                registrar_evento(
                    request=request,
                    modulo="proyectos",
                    funcionalidad="hitos",
                    accion="EDITAR",
                    instancia=hito,
                    antes=antes,
                    entidad=proyecto.entidad,
                )
        except IntegrityError:
            return Response(
                {"detail": "Ya existe un hito con ese orden o nombre."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        hito_autorizado = self.get_object()
        try:
            with transaction.atomic():
                proyecto = self._bloquear_proyecto(hito_autorizado.proyecto_id)
                hito = (
                    HitoProyecto.objects.select_for_update()
                    .select_related("proyecto", "proyecto__entidad")
                    .get(pk=hito_autorizado.pk, proyecto_id=proyecto.pk)
                )
                if proyecto.estado not in ESTADOS_EDITABLES:
                    return Response(
                        {
                            "detail": (
                                "El cronograma ya no puede modificarse en este estado."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )
                if hito.seguimientos.exists():
                    return Response(
                        {
                            "detail": (
                                "No se puede eliminar un hito con seguimientos vinculados."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )
                antes = serializar_instancia(hito)
                registrar_evento(
                    request=request,
                    modulo="proyectos",
                    funcionalidad="hitos",
                    accion="ELIMINAR",
                    instancia=hito,
                    antes=antes,
                    despues={},
                    entidad=proyecto.entidad,
                )
                hito.delete()
        except ProtectedError:
            return Response(
                {"detail": "No se puede eliminar el hito porque mantiene relaciones protegidas."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class SeguimientoProyectoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SeguimientoProyectoSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "proyectos.ver",
        "retrieve": "proyectos.ver",
    }
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "proyecto__codigo",
        "proyecto__nombre",
        "hito__nombre",
        "observacion",
        "registrado_por__username",
    ]
    ordering_fields = [
        "id",
        "fecha_registro",
        "avance_fisico",
        "avance_financiero",
        "fecha_creacion",
    ]
    ordering = ["-fecha_registro", "-fecha_creacion"]

    def get_queryset(self):
        proyectos = filtrar_proyectos_por_alcance(
            ProyectoInversion.objects.all(),
            self.request.user,
        )
        return SeguimientoProyecto.objects.select_related(
            "proyecto",
            "proyecto__entidad",
            "hito",
            "registrado_por",
        ).filter(proyecto__in=proyectos)
