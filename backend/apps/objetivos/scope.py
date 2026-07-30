"""Alcance de objetivos y alineaciones derivado de planes visibles."""

from django.db.models import Q

from apps.configuracion.scope import (
    ALCANCES_GLOBALES,
    ALCANCES_INSTITUCIONALES,
    filtrar_queryset_por_entidad,
    obtener_alcance_usuario,
)
from apps.planes.scope import ESTADOS_EN_REVISION


def filtrar_objetivos_por_alcance(queryset, usuario):
    """Incluye objetivos propios y los usados en expedientes revisables."""

    alcance = obtener_alcance_usuario(usuario)
    if alcance in ALCANCES_GLOBALES:
        return queryset
    if alcance not in ALCANCES_INSTITUCIONALES:
        return queryset.none()

    entidad_id = getattr(usuario, "entidad_id", None)
    if entidad_id is None:
        return queryset.none()

    if alcance == "REVISION_ENTIDAD":
        return queryset.filter(
            Q(entidad_id=entidad_id)
            | Q(metas__plan__estado__in=ESTADOS_EN_REVISION)
            | Q(metas__plan__historial_estados__usuario_id=usuario.pk)
            | Q(metas__plan__revisor_id=usuario.pk)
            | Q(metas__plan__aprobado_por_id=usuario.pk)
        ).distinct()

    return filtrar_queryset_por_entidad(queryset, usuario, "entidad")


def filtrar_alineaciones_por_alcance(queryset, usuario):
    """Aplica a la matriz el mismo expediente visible que a sus objetivos."""

    alcance = obtener_alcance_usuario(usuario)
    if alcance in ALCANCES_GLOBALES:
        return queryset
    if alcance not in ALCANCES_INSTITUCIONALES:
        return queryset.none()

    entidad_id = getattr(usuario, "entidad_id", None)
    if entidad_id is None:
        return queryset.none()

    if alcance == "REVISION_ENTIDAD":
        return queryset.filter(
            Q(objetivo_estrategico__entidad_id=entidad_id)
            | Q(
                objetivo_estrategico__metas__plan__estado__in=(
                    ESTADOS_EN_REVISION
                )
            )
            | Q(
                objetivo_estrategico__metas__plan__historial_estados__usuario_id=(
                    usuario.pk
                )
            )
            | Q(
                objetivo_estrategico__metas__plan__revisor_id=usuario.pk
            )
            | Q(
                objetivo_estrategico__metas__plan__aprobado_por_id=usuario.pk
            )
        ).distinct()

    return filtrar_queryset_por_entidad(
        queryset,
        usuario,
        "objetivo_estrategico__entidad",
    )
