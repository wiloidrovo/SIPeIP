"""Cálculos deterministas de seguimiento para la planificación institucional.

Las funciones de este módulo no persisten datos ni cambian estados. Reciben
instancias del dominio, calculan resultados reproducibles y devuelven valores
listos para ser serializados por la capa API.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable

from django.utils import timezone


DOS_DECIMALES = Decimal("0.01")
CIEN = Decimal("100.00")
CERO = Decimal("0.00")
TOLERANCIA_RIESGO = Decimal("10.00")

ESTADO_SIN_DATOS = "SIN_DATOS"
ESTADO_SIN_AVANCES = "SIN_AVANCES"
ESTADO_PENDIENTE_VALIDACION = "PENDIENTE_VALIDACION"
ESTADO_EN_CURSO = "EN_CURSO"
ESTADO_EN_RIESGO = "EN_RIESGO"
ESTADO_CUMPLIDO = "CUMPLIDO"
ESTADO_INCUMPLIDO = "INCUMPLIDO"

ETIQUETAS_ESTADO = {
    ESTADO_SIN_DATOS: "Sin datos",
    ESTADO_SIN_AVANCES: "Sin avances",
    ESTADO_PENDIENTE_VALIDACION: "Pendiente de validación",
    ESTADO_EN_CURSO: "En curso",
    ESTADO_EN_RIESGO: "En riesgo",
    ESTADO_CUMPLIDO: "Cumplido",
    ESTADO_INCUMPLIDO: "Incumplido",
}

MESES_POR_FRECUENCIA = {
    "MENSUAL": 1,
    "TRIMESTRAL": 3,
    "SEMESTRAL": 6,
    "ANUAL": 12,
}


def _decimal(valor: Any, predeterminado: Decimal = CERO) -> Decimal:
    if valor is None:
        return predeterminado
    return Decimal(str(valor))


def _porcentaje(valor: Decimal) -> Decimal:
    return min(CIEN, max(CERO, valor)).quantize(
        DOS_DECIMALES,
        rounding=ROUND_HALF_UP,
    )


def _fecha(valor: Any) -> date | None:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        return date.fromisoformat(valor)
    return None


def _elementos_relacion(relacion: Any) -> list[Any]:
    if relacion is None:
        return []
    if hasattr(relacion, "all"):
        return list(relacion.all())
    return list(relacion)


def _promedio_ponderado(
    elementos: Iterable[tuple[Decimal, Decimal]],
) -> Decimal:
    total_ponderacion = CERO
    acumulado = CERO
    for progreso, ponderacion in elementos:
        peso = max(CERO, _decimal(ponderacion))
        acumulado += _porcentaje(progreso) * peso
        total_ponderacion += peso
    if total_ponderacion <= 0:
        return CERO
    return _porcentaje(acumulado / total_ponderacion)


def _avance_esperado(fecha_inicio: Any, fecha_fin: Any, hoy: date) -> Decimal:
    inicio = _fecha(fecha_inicio)
    fin = _fecha(fecha_fin)
    if inicio is None or fin is None:
        return CERO
    if hoy < inicio:
        return CERO
    if hoy >= fin:
        return CIEN
    duracion = (fin - inicio).days
    if duracion <= 0:
        return CIEN
    transcurrido = (hoy - inicio).days
    return _porcentaje(
        Decimal(transcurrido) * CIEN / Decimal(duracion)
    )


def _sumar_meses(fecha_base: date, meses: int) -> date:
    indice_mes = fecha_base.month - 1 + meses
    anio = fecha_base.year + indice_mes // 12
    mes = indice_mes % 12 + 1
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    return date(anio, mes, min(fecha_base.day, ultimo_dia))


def _orden_avance(avance: Any) -> tuple[date, str, int]:
    return (
        _fecha(getattr(avance, "fecha_registro", None)) or date.min,
        str(getattr(avance, "fecha_creacion", "") or ""),
        int(getattr(avance, "pk", 0) or 0),
    )


def _resumen_avance(avance: Any | None) -> dict[str, Any] | None:
    if avance is None:
        return None
    return {
        "id": getattr(avance, "pk", None),
        "fecha_registro": _fecha(getattr(avance, "fecha_registro", None)),
        "valor": _decimal(getattr(avance, "valor", None)),
        "observacion": getattr(avance, "observacion", "") or "",
        "evidencia": getattr(avance, "evidencia", "") or "",
    }


def etiqueta_estado_seguimiento(codigo: str) -> str:
    """Devuelve una etiqueta estable en español para el código calculado."""

    return ETIQUETAS_ESTADO.get(codigo, "Sin estado")


def calcular_progreso_indicador(indicador: Any) -> Decimal:
    """Calcula avance base-meta respetando el sentido del indicador."""

    base = _decimal(getattr(indicador, "valor_base", None))
    meta = _decimal(getattr(indicador, "valor_meta", None))
    actual = _decimal(getattr(indicador, "valor_actual", None))
    sentido = getattr(indicador, "sentido", "ASCENDENTE")

    if sentido == "DESCENDENTE":
        distancia = base - meta
        if distancia == 0:
            return CIEN if actual <= meta else CERO
        return _porcentaje((base - actual) * CIEN / distancia)

    distancia = meta - base
    if distancia == 0:
        return CIEN if actual >= meta else CERO
    return _porcentaje((actual - base) * CIEN / distancia)


def calcular_proxima_medicion(
    indicador: Any,
    *,
    ultimo_avance: Any | None = None,
) -> date | None:
    """Calcula el siguiente corte sin superar el periodo de la meta."""

    meta = getattr(indicador, "meta", None)
    if meta is None:
        return None
    inicio = _fecha(getattr(meta, "fecha_inicio", None))
    fin = _fecha(getattr(meta, "fecha_fin", None))
    if inicio is None or fin is None:
        return None

    if ultimo_avance is None:
        avances = _elementos_relacion(getattr(indicador, "avances", None))
        ultimo_avance = max(avances, key=_orden_avance, default=None)

    ultima_fecha = _fecha(getattr(ultimo_avance, "fecha_registro", None))
    if ultima_fecha is None:
        return inicio
    if ultima_fecha >= fin:
        return None

    meses = MESES_POR_FRECUENCIA.get(
        getattr(indicador, "frecuencia", ""),
        3,
    )
    return min(_sumar_meses(ultima_fecha, meses), fin)


def calcular_seguimiento_indicador(
    indicador: Any,
    hoy: date | None = None,
) -> dict[str, Any]:
    """Resume progreso, oportunidad y tendencia de un indicador."""

    fecha_referencia = hoy or timezone.localdate()
    meta = getattr(indicador, "meta", None)
    avances = sorted(
        _elementos_relacion(getattr(indicador, "avances", None)),
        key=_orden_avance,
    )
    ultimo = avances[-1] if avances else None
    progreso = calcular_progreso_indicador(indicador)
    esperado = _avance_esperado(
        getattr(meta, "fecha_inicio", None),
        getattr(meta, "fecha_fin", None),
        fecha_referencia,
    )
    proxima = calcular_proxima_medicion(
        indicador,
        ultimo_avance=ultimo,
    )
    atrasado = bool(
        proxima
        and proxima < fecha_referencia
        and progreso < CIEN
    )
    fin_meta = _fecha(getattr(meta, "fecha_fin", None))

    if not getattr(indicador, "validado", False):
        estado = ESTADO_PENDIENTE_VALIDACION
    elif progreso >= CIEN:
        estado = ESTADO_CUMPLIDO
    elif fin_meta and fecha_referencia > fin_meta:
        estado = ESTADO_INCUMPLIDO
    elif not avances:
        estado = ESTADO_SIN_AVANCES
    elif atrasado or progreso + TOLERANCIA_RIESGO < esperado:
        estado = ESTADO_EN_RIESGO
    else:
        estado = ESTADO_EN_CURSO

    tendencia = "SIN_DATOS"
    if len(avances) >= 2:
        anterior = _decimal(getattr(avances[-2], "valor", None))
        actual = _decimal(getattr(avances[-1], "valor", None))
        if actual == anterior:
            tendencia = "ESTABLE"
        elif getattr(indicador, "sentido", "ASCENDENTE") == "DESCENDENTE":
            tendencia = "MEJORA" if actual < anterior else "RETROCESO"
        else:
            tendencia = "MEJORA" if actual > anterior else "RETROCESO"

    return {
        "progreso": progreso,
        "avance_esperado": esperado,
        "estado_seguimiento": estado,
        "etiqueta_estado_seguimiento": etiqueta_estado_seguimiento(estado),
        "ultimo_avance": _resumen_avance(ultimo),
        "proxima_medicion": proxima,
        "medicion_atrasada": atrasado,
        "tendencia": tendencia,
    }


def _estado_agregado(
    *,
    progreso: Decimal,
    fecha_fin: Any,
    estados_hijos: Iterable[str],
    hoy: date,
    estado_cerrado: bool = False,
) -> str:
    estados = set(estados_hijos)
    fin = _fecha(fecha_fin)
    if ESTADO_PENDIENTE_VALIDACION in estados:
        return ESTADO_PENDIENTE_VALIDACION
    if progreso >= CIEN:
        return ESTADO_CUMPLIDO
    if estado_cerrado or (fin and hoy > fin):
        return ESTADO_INCUMPLIDO
    if not estados or estados == {ESTADO_SIN_DATOS}:
        return ESTADO_SIN_DATOS
    if estados.issubset({ESTADO_SIN_AVANCES, ESTADO_SIN_DATOS}):
        return ESTADO_SIN_AVANCES
    if estados.intersection({ESTADO_EN_RIESGO, ESTADO_INCUMPLIDO}):
        return ESTADO_EN_RIESGO
    return ESTADO_EN_CURSO


def calcular_seguimiento_meta(
    meta: Any,
    hoy: date | None = None,
) -> dict[str, Any]:
    """Agrega indicadores activos usando su ponderación relativa."""

    fecha_referencia = hoy or timezone.localdate()
    indicadores = [
        indicador
        for indicador in _elementos_relacion(
            getattr(meta, "indicadores", None)
        )
        if getattr(indicador, "activo", True)
    ]
    seguimientos = [
        calcular_seguimiento_indicador(indicador, fecha_referencia)
        for indicador in indicadores
    ]
    progreso = _promedio_ponderado(
        (
            seguimiento["progreso"],
            _decimal(getattr(indicador, "ponderacion", Decimal("100.00"))),
        )
        for indicador, seguimiento in zip(indicadores, seguimientos)
    )
    estado = _estado_agregado(
        progreso=progreso,
        fecha_fin=getattr(meta, "fecha_fin", None),
        estados_hijos=(
            seguimiento["estado_seguimiento"]
            for seguimiento in seguimientos
        ),
        hoy=fecha_referencia,
        estado_cerrado=getattr(meta, "estado", "") == "CERRADA",
    )

    proximas = [
        seguimiento["proxima_medicion"]
        for seguimiento in seguimientos
        if seguimiento["proxima_medicion"] is not None
    ]
    ultimos = [
        seguimiento["ultimo_avance"]
        for seguimiento in seguimientos
        if seguimiento["ultimo_avance"] is not None
    ]
    ultimo_avance = max(
        ultimos,
        key=lambda item: item["fecha_registro"] or date.min,
        default=None,
    )

    return {
        "progreso": progreso,
        "avance_esperado": _avance_esperado(
            getattr(meta, "fecha_inicio", None),
            getattr(meta, "fecha_fin", None),
            fecha_referencia,
        ),
        "estado_seguimiento": estado,
        "etiqueta_estado_seguimiento": etiqueta_estado_seguimiento(estado),
        "proxima_medicion": min(proximas) if proximas else None,
        "ultimo_avance": ultimo_avance,
        "indicadores_total": len(indicadores),
        "indicadores_cumplidos": sum(
            seguimiento["estado_seguimiento"] == ESTADO_CUMPLIDO
            for seguimiento in seguimientos
        ),
        "indicadores_en_riesgo": sum(
            seguimiento["estado_seguimiento"]
            in {ESTADO_EN_RIESGO, ESTADO_INCUMPLIDO}
            for seguimiento in seguimientos
        ),
        "indicadores_pendientes_validacion": sum(
            seguimiento["estado_seguimiento"]
            == ESTADO_PENDIENTE_VALIDACION
            for seguimiento in seguimientos
        ),
    }


def calcular_seguimiento_objetivo(
    objetivo: Any,
    metas: Iterable[Any] | None = None,
    hoy: date | None = None,
) -> dict[str, Any]:
    """Agrega las metas de un objetivo; permite acotarlas a un plan."""

    fecha_referencia = hoy or timezone.localdate()
    metas_objetivo = (
        list(metas)
        if metas is not None
        else _elementos_relacion(getattr(objetivo, "metas", None))
    )
    metas_objetivo = [
        meta
        for meta in metas_objetivo
        if getattr(meta, "estado", "") != "ARCHIVADA"
    ]
    seguimientos = [
        calcular_seguimiento_meta(meta, fecha_referencia)
        for meta in metas_objetivo
    ]
    progreso = _promedio_ponderado(
        (seguimiento["progreso"], Decimal("1.00"))
        for seguimiento in seguimientos
    )
    estado = _estado_agregado(
        progreso=progreso,
        fecha_fin=max(
            (
                _fecha(getattr(meta, "fecha_fin", None))
                for meta in metas_objetivo
            ),
            default=None,
        ),
        estados_hijos=(
            seguimiento["estado_seguimiento"]
            for seguimiento in seguimientos
        ),
        hoy=fecha_referencia,
    )
    proximas = [
        seguimiento["proxima_medicion"]
        for seguimiento in seguimientos
        if seguimiento["proxima_medicion"] is not None
    ]
    ultimos = [
        seguimiento["ultimo_avance"]
        for seguimiento in seguimientos
        if seguimiento["ultimo_avance"] is not None
    ]

    return {
        "progreso": progreso,
        "estado_seguimiento": estado,
        "etiqueta_estado_seguimiento": etiqueta_estado_seguimiento(estado),
        "proxima_medicion": min(proximas) if proximas else None,
        "ultimo_avance": max(
            ultimos,
            key=lambda item: item["fecha_registro"] or date.min,
            default=None,
        ),
        "metas_total": len(metas_objetivo),
        "metas_cumplidas": sum(
            seguimiento["estado_seguimiento"] == ESTADO_CUMPLIDO
            for seguimiento in seguimientos
        ),
        "metas_en_riesgo": sum(
            seguimiento["estado_seguimiento"]
            in {ESTADO_EN_RIESGO, ESTADO_INCUMPLIDO}
            for seguimiento in seguimientos
        ),
    }


def calcular_seguimiento_plan(
    plan: Any,
    hoy: date | None = None,
) -> dict[str, Any]:
    """Consolida las metas no archivadas de un plan institucional."""

    fecha_referencia = hoy or timezone.localdate()
    metas = [
        meta
        for meta in _elementos_relacion(getattr(plan, "metas", None))
        if getattr(meta, "estado", "") != "ARCHIVADA"
    ]
    seguimientos = [
        calcular_seguimiento_meta(meta, fecha_referencia)
        for meta in metas
    ]
    progreso = _promedio_ponderado(
        (seguimiento["progreso"], Decimal("1.00"))
        for seguimiento in seguimientos
    )
    estado = _estado_agregado(
        progreso=progreso,
        fecha_fin=getattr(plan, "periodo_fin", None),
        estados_hijos=(
            seguimiento["estado_seguimiento"]
            for seguimiento in seguimientos
        ),
        hoy=fecha_referencia,
    )
    proximas = [
        seguimiento["proxima_medicion"]
        for seguimiento in seguimientos
        if seguimiento["proxima_medicion"] is not None
    ]
    ultimos = [
        seguimiento["ultimo_avance"]
        for seguimiento in seguimientos
        if seguimiento["ultimo_avance"] is not None
    ]
    objetivos_ids = {
        getattr(meta, "objetivo_estrategico_id", None)
        for meta in metas
        if getattr(meta, "objetivo_estrategico_id", None) is not None
    }

    return {
        "progreso": progreso,
        "avance_esperado": _avance_esperado(
            getattr(plan, "periodo_inicio", None),
            getattr(plan, "periodo_fin", None),
            fecha_referencia,
        ),
        "estado_seguimiento": estado,
        "etiqueta_estado_seguimiento": etiqueta_estado_seguimiento(estado),
        "proxima_medicion": min(proximas) if proximas else None,
        "ultimo_avance": max(
            ultimos,
            key=lambda item: item["fecha_registro"] or date.min,
            default=None,
        ),
        "objetivos_total": len(objetivos_ids),
        "metas_total": len(metas),
        "metas_cumplidas": sum(
            seguimiento["estado_seguimiento"] == ESTADO_CUMPLIDO
            for seguimiento in seguimientos
        ),
        "metas_en_riesgo": sum(
            seguimiento["estado_seguimiento"]
            in {ESTADO_EN_RIESGO, ESTADO_INCUMPLIDO}
            for seguimiento in seguimientos
        ),
        "metas_pendientes_validacion": sum(
            seguimiento["estado_seguimiento"]
            == ESTADO_PENDIENTE_VALIDACION
            for seguimiento in seguimientos
        ),
    }
