from datetime import timedelta

from django.apps import apps
from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.configuracion.scope import (
    filtrar_queryset_por_entidad,
    obtener_alcance_usuario,
)
from apps.reportes.datasets import DATASETS


def _planes_visibles(usuario):
    Plan = apps.get_model("planes", "Plan")
    queryset = filtrar_queryset_por_entidad(Plan.objects.all(), usuario, "entidad")
    if obtener_alcance_usuario(usuario) in {"ENTIDAD", "PROPIO_ASIGNADO"}:
        queryset = queryset.filter(Q(creado_por=usuario) | Q(responsable=usuario))
    return queryset.distinct()


def _widget(codigo, titulo, valor, ruta, detalle=""):
    return {
        "codigo": codigo,
        "titulo": titulo,
        "valor": valor,
        "detalle": detalle,
        "ruta": ruta,
    }


def _widgets_administracion(usuario, permisos):
    widgets = []
    if "usuarios.ver" in permisos:
        Usuario = apps.get_model("usuarios", "Usuario")
        usuarios = filtrar_queryset_por_entidad(Usuario.objects.all(), usuario, "entidad")
        widgets.extend(
            [
                _widget(
                    "usuarios_activos",
                    "Usuarios activos",
                    usuarios.filter(estado="ACTIVO", is_active=True).count(),
                    "/usuarios",
                ),
                _widget(
                    "usuarios_bloqueados",
                    "Usuarios bloqueados",
                    usuarios.filter(estado="BLOQUEADO").count(),
                    "/usuarios",
                ),
            ]
        )
    if "roles.ver" in permisos:
        Rol = apps.get_model("roles", "Rol")
        widgets.append(
            _widget("roles", "Roles configurados", Rol.objects.filter(activo=True).count(), "/roles")
        )
    if "configuracion.ver" in permisos:
        Entidad = apps.get_model("configuracion", "EntidadInstitucional")
        entidades = filtrar_queryset_por_entidad(Entidad.objects.all(), usuario, "pk")
        widgets.append(
            _widget("entidades", "Entidades registradas", entidades.count(), "/configuracion/entidades")
        )
    if "auditoria.ver" in permisos:
        Evento = apps.get_model("auditoria", "EventoAuditoria")
        eventos = filtrar_queryset_por_entidad(Evento.objects.all(), usuario, "entidad")
        desde = timezone.now() - timedelta(days=7)
        widgets.append(
            _widget(
                "actividad_reciente",
                "Actividad de los últimos 7 días",
                eventos.filter(fecha_hora__gte=desde).count(),
                "/auditoria",
            )
        )
    return widgets


def _widgets_planificacion(usuario, permisos, planes):
    widgets = []
    if "planes.ver" in permisos:
        widgets.extend(
            [
                _widget("planes_borrador", "Planes en borrador", planes.filter(estado="BORRADOR").count(), "/planes"),
                _widget("planes_revision", "Planes enviados a revisión", planes.filter(estado="EN_REVISION").count(), "/planes"),
                _widget("planes_devueltos", "Planes devueltos", planes.filter(estado="DEVUELTO").count(), "/planes"),
            ]
        )
    if "metas.ver" in permisos:
        Meta = apps.get_model("metas", "Meta")
        metas = Meta.objects.filter(plan__in=planes)
        widgets.append(
            _widget("metas_activas", "Metas activas", metas.filter(estado="ACTIVA", activa=True).count(), "/metas")
        )
        hoy = timezone.localdate()
        widgets.append(
            _widget(
                "proximos_vencimientos",
                "Vencimientos próximos",
                metas.filter(fecha_fin__gte=hoy, fecha_fin__lte=hoy + timedelta(days=30)).count(),
                "/metas",
                "Metas que vencen en los próximos 30 días",
            )
        )
    if "indicadores.ver" in permisos:
        Indicador = apps.get_model("metas", "Indicador")
        indicadores = Indicador.objects.filter(meta__plan__in=planes)
        widgets.append(
            _widget(
                "indicadores_pendientes",
                "Indicadores por validar",
                indicadores.filter(validado=False, activo=True).count(),
                "/indicadores",
            )
        )
    if "reportes.ver" in permisos:
        disponibles = sum(
            1
            for especificacion in DATASETS.values()
            if all(codigo in permisos for codigo in especificacion.permisos_fuente)
        )
        widgets.append(_widget("reportes", "Reportes disponibles", disponibles, "/reportes"))
    return widgets


def _widgets_supervision(usuario, permisos, planes):
    widgets = []
    if "planes.ver" in permisos:
        widgets.extend(
            [
                _widget("bandeja_revision", "Planes por revisar", planes.filter(estado="EN_REVISION").count(), "/planes"),
                _widget(
                    "pendientes_decision",
                    "Planes pendientes de decisión",
                    planes.filter(estado="EN_REVISION_INICIADA").count(),
                    "/planes",
                ),
                _widget(
                    "planes_observados",
                    "Planes observados",
                    planes.filter(estado__in=["DEVUELTO", "RECHAZADO"]).count(),
                    "/planes",
                ),
            ]
        )
    if "indicadores.ver" in permisos:
        Indicador = apps.get_model("metas", "Indicador")
        widgets.append(
            _widget(
                "indicadores_pendientes",
                "Indicadores por validar",
                Indicador.objects.filter(meta__plan__in=planes, validado=False, activo=True).count(),
                "/indicadores",
            )
        )
    if "proyectos.ver" in permisos:
        Proyecto = apps.get_model("proyectos", "ProyectoInversion")
        proyectos = filtrar_queryset_por_entidad(Proyecto.objects.all(), usuario, "entidad")
        widgets.append(
            _widget(
                "proyectos_revision",
                "Proyectos por decidir",
                proyectos.filter(estado="EN_REVISION").count(),
                "/proyectos",
            )
        )
    if "auditoria.ver" in permisos:
        Evento = apps.get_model("auditoria", "EventoAuditoria")
        eventos = filtrar_queryset_por_entidad(Evento.objects.all(), usuario, "entidad")
        widgets.append(
            _widget(
                "actividad_reciente",
                "Actividad reciente",
                eventos.filter(fecha_hora__gte=timezone.now() - timedelta(days=7)).count(),
                "/auditoria",
            )
        )
    return widgets


def _widgets_auditoria(usuario, permisos):
    Evento = apps.get_model("auditoria", "EventoAuditoria")
    eventos = filtrar_queryset_por_entidad(Evento.objects.all(), usuario, "entidad")
    desde = timezone.now() - timedelta(days=30)
    recientes = eventos.filter(fecha_hora__gte=desde)
    widgets = [
        _widget("eventos_recientes", "Eventos de los últimos 30 días", recientes.count(), "/auditoria"),
        _widget("modulos_con_actividad", "Módulos con actividad", recientes.values("modulo").distinct().count(), "/auditoria"),
        _widget("accesos", "Accesos registrados", recientes.filter(accion="LOGIN").count(), "/auditoria"),
        _widget(
            "decisiones",
            "Aprobaciones y rechazos",
            recientes.filter(accion__in=["APROBAR", "RECHAZAR"]).count(),
            "/auditoria",
        ),
    ]
    if "reportes.ver" in permisos:
        disponibles = sum(
            1
            for especificacion in DATASETS.values()
            if all(codigo in permisos for codigo in especificacion.permisos_fuente)
        )
        widgets.append(_widget("reportes_control", "Reportes de control", disponibles, "/reportes"))
    return widgets


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        usuario = request.user
        permisos = set(usuario.get_sipeip_permissions())
        alcance = obtener_alcance_usuario(usuario)
        planes = _planes_visibles(usuario)

        administra = bool(
            permisos.intersection({"usuarios.editar", "roles.asignar_permisos", "configuracion.gestionar"})
        )
        supervisa = bool(permisos.intersection({"planes.revisar", "planes.aprobar", "planes.rechazar"}))
        solo_control = "auditoria.ver" in permisos and not permisos.intersection(
            {"usuarios.editar", "planes.editar", "metas.editar", "indicadores.editar", "proyectos.editar"}
        )

        if administra:
            widgets = _widgets_administracion(usuario, permisos)
            if len(widgets) < 4:
                widgets.extend(_widgets_planificacion(usuario, permisos, planes))
        elif supervisa:
            widgets = _widgets_supervision(usuario, permisos, planes)
            if len(widgets) < 4:
                widgets.extend(_widgets_planificacion(usuario, permisos, planes))
        elif solo_control:
            widgets = _widgets_auditoria(usuario, permisos)
        else:
            widgets = _widgets_planificacion(usuario, permisos, planes)

        entidad = getattr(usuario, "entidad", None)
        return Response(
            {
                "alcance": alcance,
                "entidad": (
                    {
                        "id": entidad.pk,
                        "codigo_oficial": entidad.codigo_oficial,
                        "nombre": entidad.nombre,
                    }
                    if entidad
                    else None
                ),
                "widgets": widgets[:8],
            }
        )
