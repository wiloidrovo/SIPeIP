"""Reglas de alcance para proyectos de inversión.

El alcance siempre se deriva de la identidad autenticada. Ningún parámetro
del cliente puede ampliar los registros visibles u operables.
"""

from django.db.models import Q

from apps.configuracion.scope import (
    ALCANCES_GLOBALES,
    ALCANCES_INSTITUCIONALES,
    obtener_alcance_usuario,
)


ALCANCES_PROPIOS = frozenset({"ENTIDAD", "PROPIO_ASIGNADO"})


def filtrar_proyectos_por_alcance(queryset, usuario):
    """Aplica entidad y, cuando corresponde, propiedad o asignación.

    Los alcances ``ENTIDAD`` y ``PROPIO_ASIGNADO`` reproducen la regla de
    planes: solo registros creados por la persona o asignados a ella. Los
    perfiles de revisión y auditoría conservan la vista institucional porque
    sus permisos de mutación son distintos y explícitos.
    """

    alcance = obtener_alcance_usuario(usuario)
    if alcance in ALCANCES_GLOBALES:
        return queryset
    if alcance not in ALCANCES_INSTITUCIONALES:
        return queryset.none()

    entidad_id = getattr(usuario, "entidad_id", None)
    if entidad_id is None:
        return queryset.none()

    queryset = queryset.filter(entidad_id=entidad_id)
    if alcance in ALCANCES_PROPIOS:
        queryset = queryset.filter(
            Q(creado_por=usuario) | Q(responsable=usuario)
        )
    return queryset.distinct()


def proyecto_esta_en_alcance(proyecto, usuario):
    """Comprueba el alcance con una consulta que deniega por defecto."""

    if proyecto is None or getattr(proyecto, "pk", None) is None:
        return False
    return filtrar_proyectos_por_alcance(
        proyecto.__class__._default_manager.all(),
        usuario,
    ).filter(pk=proyecto.pk).exists()
