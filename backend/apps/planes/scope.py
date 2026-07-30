"""Alcance de registros relacionados con el flujo de planes.

Los perfiles institucionales conservan el límite de su entidad. El alcance de
revisión añade una bandeja interinstitucional acotada: únicamente planes
enviados a revisión y registros de planes en los que el usuario ya intervino.
"""

from django.db.models import Q

from apps.configuracion.scope import (
    ALCANCES_GLOBALES,
    ALCANCES_INSTITUCIONALES,
    filtrar_queryset_por_entidad,
    obtener_alcance_usuario,
)

from .models import Plan


ESTADOS_EN_REVISION = frozenset(
    {
        Plan.EstadoPlan.EN_REVISION,
        Plan.EstadoPlan.EN_REVISION_INICIADA,
    }
)


def _ruta_plan(plan_lookup, campo):
    prefijo = f"{plan_lookup}__" if plan_lookup else ""
    return f"{prefijo}{campo}"


def filtrar_queryset_por_alcance_plan(queryset, usuario, plan_lookup=""):
    """Filtra un queryset directo o relacionado con ``Plan``.

    ``plan_lookup`` es vacío para un queryset de planes, ``plan`` para metas y
    ``meta__plan`` para indicadores o avances. Un revisor puede consultar:

    - todos los planes de su propia institución;
    - planes de otras instituciones mientras están en revisión;
    - planes de otras instituciones en los que ya registró una transición.

    Ningún parámetro recibido desde el cliente amplía este alcance.
    """

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
            Q(**{_ruta_plan(plan_lookup, "entidad_id"): entidad_id})
            | Q(
                **{
                    _ruta_plan(plan_lookup, "estado__in"): ESTADOS_EN_REVISION
                }
            )
            | Q(
                **{
                    _ruta_plan(
                        plan_lookup,
                        "historial_estados__usuario_id",
                    ): usuario.pk
                }
            )
            | Q(
                **{
                    _ruta_plan(plan_lookup, "revisor_id"): usuario.pk,
                }
            )
            | Q(
                **{
                    _ruta_plan(plan_lookup, "aprobado_por_id"): usuario.pk,
                }
            )
        ).distinct()

    entidad_lookup = (
        f"{plan_lookup}__entidad" if plan_lookup else "entidad"
    )
    return filtrar_queryset_por_entidad(
        queryset,
        usuario,
        entidad_lookup,
    )
