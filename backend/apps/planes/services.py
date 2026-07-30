"""Reglas de integridad y seguimiento del expediente de un plan.

Este módulo concentra las comprobaciones que condicionan las transiciones del
flujo. La interfaz puede explicar los bloqueos, pero la decisión autoritativa
se mantiene en el backend.
"""

from collections import defaultdict
from decimal import Decimal

from django.db.models import Prefetch

from apps.metas.models import Indicador, Meta
from apps.objetivos.models import Alineacion, EstadoCatalogo

from .models import Plan


def obtener_metas_detalladas(plan):
    """Obtiene la estructura operativa del plan con consultas acotadas."""

    alineaciones = Alineacion.objects.select_related(
        "objetivo_pnd__eje",
        "ods",
        "usuario_creador",
        "usuario_validador",
    ).order_by("ods__numero", "objetivo_pnd__codigo")
    indicadores = Indicador.objects.select_related(
        "validado_por",
    ).prefetch_related("avances__registrado_por")
    return list(
        Meta.objects.filter(plan=plan)
        .select_related(
            "plan__entidad",
            "objetivo_estrategico__entidad",
        )
        .prefetch_related(
            Prefetch(
                "objetivo_estrategico__alineaciones",
                queryset=alineaciones,
            ),
            Prefetch("indicadores", queryset=indicadores),
        )
        .order_by("objetivo_estrategico__codigo", "fecha_inicio", "id")
    )


def _agregar_bloqueo(destino, codigo, mensaje, **contexto):
    destino.append(
        {
            "codigo": codigo,
            "mensaje": mensaje,
            **contexto,
        }
    )


def _indicador_es_coherente(indicador):
    if indicador.sentido == Indicador.SentidoMedicion.ASCENDENTE:
        return indicador.valor_meta > indicador.valor_base
    if indicador.sentido == Indicador.SentidoMedicion.DESCENDENTE:
        return indicador.valor_meta < indicador.valor_base
    return False


def evaluar_integridad_plan(plan, metas=None):
    """Evalúa si un plan puede enviarse y si puede aprobarse.

    ``bloqueos_revision`` contiene estructura faltante o incoherente.
    ``bloqueos_aprobacion`` añade las validaciones que corresponden al
    supervisor. Se devuelven códigos estables para pruebas y mensajes legibles
    para la interfaz.
    """

    if metas is None:
        cache = getattr(plan, "_prefetched_objects_cache", {})
        metas = (
            list(plan.metas.all())
            if "metas" in cache
            else obtener_metas_detalladas(plan)
        )
    bloqueos_revision = []
    bloqueos_validacion = []
    advertencias = []

    if getattr(plan.entidad, "estado", None) != "ACTIVA":
        _agregar_bloqueo(
            bloqueos_revision,
            "ENTIDAD_INACTIVA",
            "La entidad institucional del plan debe permanecer activa.",
        )
    if not (plan.descripcion or "").strip():
        _agregar_bloqueo(
            bloqueos_revision,
            "PLAN_SIN_DESCRIPCION",
            "El plan debe incluir una descripción que permita evaluar su contenido.",
        )
    if plan.responsable_id is None:
        _agregar_bloqueo(
            bloqueos_revision,
            "PLAN_SIN_RESPONSABLE",
            "El plan debe tener una persona responsable.",
        )
    elif (
        not plan.responsable.is_active
        or getattr(plan.responsable, "estado", "ACTIVO") != "ACTIVO"
    ):
        _agregar_bloqueo(
            bloqueos_revision,
            "RESPONSABLE_INACTIVO",
            "La persona responsable del plan está inactiva o bloqueada.",
        )

    if not metas:
        _agregar_bloqueo(
            bloqueos_revision,
            "PLAN_SIN_METAS",
            "El plan debe contener al menos una meta institucional.",
        )

    objetivos_revisados = set()
    for meta in metas:
        contexto_meta = {"meta_id": meta.pk, "meta": meta.nombre}
        if meta.objetivo_estrategico_id is None:
            _agregar_bloqueo(
                bloqueos_revision,
                "META_SIN_OBJETIVO",
                f"La meta «{meta.nombre}» no tiene un objetivo estratégico.",
                **contexto_meta,
            )
            continue

        objetivo = meta.objetivo_estrategico
        contexto_objetivo = {
            "objetivo_id": objetivo.pk,
            "objetivo": f"{objetivo.codigo} - {objetivo.nombre}",
        }
        if objetivo.entidad_id != plan.entidad_id:
            _agregar_bloqueo(
                bloqueos_revision,
                "OBJETIVO_DE_OTRA_ENTIDAD",
                f"El objetivo «{objetivo.codigo}» no pertenece a la entidad del plan.",
                **contexto_meta,
                **contexto_objetivo,
            )
        if objetivo.estado != EstadoCatalogo.ACTIVO:
            _agregar_bloqueo(
                bloqueos_revision,
                "OBJETIVO_INACTIVO",
                f"El objetivo «{objetivo.codigo}» está inactivo.",
                **contexto_meta,
                **contexto_objetivo,
            )

        if objetivo.pk not in objetivos_revisados:
            objetivos_revisados.add(objetivo.pk)
            alineaciones = list(objetivo.alineaciones.all())
            alineaciones_activas = []
            for alineacion in alineaciones:
                catalogos_activos = (
                    alineacion.objetivo_estrategico.estado
                    == EstadoCatalogo.ACTIVO
                    and alineacion.objetivo_pnd.estado
                    == EstadoCatalogo.ACTIVO
                    and alineacion.objetivo_pnd.eje.estado
                    == EstadoCatalogo.ACTIVO
                    and alineacion.ods.estado
                    == EstadoCatalogo.ACTIVO
                )
                if catalogos_activos:
                    alineaciones_activas.append(alineacion)
                    continue
                _agregar_bloqueo(
                    bloqueos_revision,
                    "ALINEACION_CON_CATALOGO_INACTIVO",
                    (
                        f"La alineación PND/ODS del objetivo "
                        f"«{objetivo.codigo}» contiene un catálogo inactivo."
                    ),
                    alineacion_id=alineacion.pk,
                    **contexto_objetivo,
                )
            utilizables = [
                item
                for item in alineaciones_activas
                if item.estado != Alineacion.EstadoAlineacion.RECHAZADA
            ]
            validadas = [
                item
                for item in alineaciones_activas
                if item.estado == Alineacion.EstadoAlineacion.VALIDADA
            ]
            if not utilizables:
                _agregar_bloqueo(
                    bloqueos_revision,
                    "OBJETIVO_SIN_ALINEACION",
                    (
                        f"El objetivo «{objetivo.codigo}» debe relacionarse con "
                        "un objetivo PND y un ODS."
                    ),
                    **contexto_objetivo,
                )
            if not validadas:
                _agregar_bloqueo(
                    bloqueos_validacion,
                    "ALINEACION_SIN_VALIDAR",
                    (
                        f"La alineación PND/ODS del objetivo "
                        f"«{objetivo.codigo}» aún no ha sido validada."
                    ),
                    **contexto_objetivo,
                )

        if meta.plan_id != plan.pk:
            _agregar_bloqueo(
                bloqueos_revision,
                "META_DE_OTRO_PLAN",
                f"La meta «{meta.nombre}» no pertenece al plan evaluado.",
                **contexto_meta,
            )
        if not meta.activa or meta.estado != Meta.EstadoMeta.ACTIVA:
            _agregar_bloqueo(
                bloqueos_revision,
                "META_NO_ACTIVA",
                f"La meta «{meta.nombre}» debe estar activa.",
                **contexto_meta,
            )
        if meta.fecha_inicio < plan.periodo_inicio or meta.fecha_fin > plan.periodo_fin:
            _agregar_bloqueo(
                bloqueos_revision,
                "META_FUERA_DEL_PERIODO",
                (
                    f"Las fechas de la meta «{meta.nombre}» deben estar dentro "
                    "del periodo del plan."
                ),
                **contexto_meta,
            )

        indicadores = [item for item in meta.indicadores.all() if item.activo]
        if not indicadores:
            _agregar_bloqueo(
                bloqueos_revision,
                "META_SIN_INDICADORES",
                f"La meta «{meta.nombre}» debe tener al menos un indicador activo.",
                **contexto_meta,
            )
            continue

        total_ponderacion = sum(
            (item.ponderacion for item in indicadores),
            Decimal("0"),
        )
        if total_ponderacion != Decimal("100.00"):
            _agregar_bloqueo(
                bloqueos_revision,
                "PONDERACION_INVALIDA",
                (
                    f"Los indicadores activos de la meta «{meta.nombre}» deben "
                    f"sumar 100 %; actualmente suman {total_ponderacion} %."
                ),
                **contexto_meta,
            )

        for indicador in indicadores:
            contexto_indicador = {
                "indicador_id": indicador.pk,
                "indicador": indicador.nombre,
                **contexto_meta,
            }
            if not _indicador_es_coherente(indicador):
                _agregar_bloqueo(
                    bloqueos_revision,
                    "RANGO_INDICADOR_INVALIDO",
                    (
                        f"El valor base, la meta y el sentido de medición de "
                        f"«{indicador.nombre}» no son coherentes."
                    ),
                    **contexto_indicador,
                )
            if not indicador.validado:
                _agregar_bloqueo(
                    bloqueos_validacion,
                    "INDICADOR_SIN_VALIDAR",
                    f"El indicador «{indicador.nombre}» aún no ha sido validado.",
                    **contexto_indicador,
                )

    if plan.estado == Plan.EstadoPlan.APROBADO and not metas:
        advertencias.append(
            {
                "codigo": "PLAN_APROBADO_SIN_ESTRUCTURA",
                "mensaje": (
                    "Este plan fue aprobado antes de la validación estructural "
                    "actual y requiere regularización."
                ),
            }
        )

    bloqueos_aprobacion = [*bloqueos_revision, *bloqueos_validacion]
    return {
        "completo": not bloqueos_revision,
        "listo_para_revision": not bloqueos_revision,
        "listo_para_aprobacion": not bloqueos_aprobacion,
        "bloqueos": (
            bloqueos_aprobacion
            if plan.estado
            in {
                Plan.EstadoPlan.EN_REVISION,
                Plan.EstadoPlan.EN_REVISION_INICIADA,
            }
            else bloqueos_revision
        ),
        "bloqueos_revision": bloqueos_revision,
        "bloqueos_aprobacion": bloqueos_aprobacion,
        "advertencias": advertencias,
    }


def agrupar_metas_por_objetivo(metas):
    grupos = defaultdict(list)
    for meta in metas:
        grupos[meta.objetivo_estrategico_id].append(meta)
    return grupos
