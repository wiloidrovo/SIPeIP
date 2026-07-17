from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from django.db.models import Q

from apps.auditoria.models import EventoAuditoria
from apps.configuracion.scope import (
    filtrar_queryset_por_entidad,
    obtener_alcance_usuario,
)
from apps.metas.models import AvanceIndicador, Indicador, Meta
from apps.objetivos.models import Alineacion
from apps.planes.models import Plan
from apps.proyectos.models import ProyectoInversion
from apps.usuarios.models import Usuario


MAX_FILAS_REPORTE = 5000


@dataclass(frozen=True)
class DatasetSpec:
    codigo: str
    nombre: str
    descripcion: str
    permisos_fuente: tuple[str, ...]
    columnas: tuple[tuple[str, str], ...]
    constructor: object
    filtros: tuple[str, ...] = ()
    permisos_exportacion: tuple[str, ...] = ()


def _texto_usuario(usuario):
    if usuario is None:
        return ""
    nombre = usuario.get_full_name().strip()
    return nombre or usuario.username


def _aplicar_filtro_entidad(queryset, filtros, lookup):
    entidad_id = filtros.get("entidad")
    if entidad_id:
        return queryset.filter(**{f"{lookup}_id": entidad_id})
    return queryset


def _filtrar_planes_base(queryset, usuario):
    queryset = filtrar_queryset_por_entidad(queryset, usuario, "entidad")
    if obtener_alcance_usuario(usuario) in {"ENTIDAD", "PROPIO_ASIGNADO"}:
        queryset = queryset.filter(Q(creado_por=usuario) | Q(responsable=usuario))
    return queryset.distinct()


def _filtrar_por_texto(queryset, texto, campos):
    if not texto:
        return queryset
    consulta = Q()
    for campo in campos:
        consulta |= Q(**{f"{campo}__icontains": texto})
    return queryset.filter(consulta)


def usuarios_roles(usuario, filtros):
    queryset = Usuario.objects.select_related("rol", "entidad", "unidad_organizacional")
    queryset = filtrar_queryset_por_entidad(queryset, usuario, "entidad")
    queryset = _aplicar_filtro_entidad(queryset, filtros, "entidad")
    if filtros.get("estado"):
        queryset = queryset.filter(estado=filtros["estado"])
    if filtros.get("activo") is not None:
        queryset = queryset.filter(is_active=filtros["activo"])
    queryset = _filtrar_por_texto(
        queryset,
        filtros.get("buscar"),
        ("username", "first_name", "last_name", "email", "rol__nombre"),
    )
    for item in queryset.order_by("username")[: filtros["limite"]]:
        yield {
            "usuario": item.username,
            "nombre_completo": item.get_full_name().strip(),
            "correo": item.email,
            "rol": item.rol.nombre if item.rol else "",
            "entidad": item.entidad.nombre if item.entidad else "",
            "unidad": (
                item.unidad_organizacional.nombre
                if item.unidad_organizacional
                else ""
            ),
            "estado": item.estado,
            "activo": item.is_active,
        }


def planes(usuario, filtros):
    queryset = Plan.objects.select_related("entidad", "responsable", "creado_por")
    queryset = _filtrar_planes_base(queryset, usuario)
    queryset = _aplicar_filtro_entidad(queryset, filtros, "entidad")
    if filtros.get("estado"):
        queryset = queryset.filter(estado=filtros["estado"])
    if filtros.get("activo") is not None:
        queryset = queryset.filter(activo=filtros["activo"])
    queryset = _filtrar_por_texto(
        queryset, filtros.get("buscar"), ("nombre", "descripcion", "entidad__nombre")
    )
    for item in queryset.order_by("-fecha_creacion")[: filtros["limite"]]:
        yield {
            "id": item.id,
            "entidad": item.entidad.nombre if item.entidad else "",
            "nombre": item.nombre,
            "periodo_inicio": item.periodo_inicio,
            "periodo_fin": item.periodo_fin,
            "responsable": _texto_usuario(item.responsable),
            "estado": item.estado,
            "activo": item.activo,
        }


def metas_indicadores(usuario, filtros):
    planes_visibles = _filtrar_planes_base(Plan.objects.all(), usuario)
    metas = Meta.objects.select_related("plan", "plan__entidad").filter(
        plan__in=planes_visibles
    )
    metas = _aplicar_filtro_entidad(metas, filtros, "plan__entidad")
    if filtros.get("estado"):
        metas = metas.filter(estado=filtros["estado"])
    metas = _filtrar_por_texto(
        metas, filtros.get("buscar"), ("nombre", "plan__nombre", "plan__entidad__nombre")
    )
    indicadores = Indicador.objects.select_related("meta", "meta__plan", "meta__plan__entidad").filter(
        meta__in=metas
    )
    if filtros.get("activo") is not None:
        indicadores = indicadores.filter(activo=filtros["activo"])
    for item in indicadores.order_by("meta__plan__nombre", "meta__nombre", "nombre")[: filtros["limite"]]:
        yield {
            "entidad": item.meta.plan.entidad.nombre if item.meta.plan.entidad else "",
            "plan": item.meta.plan.nombre,
            "meta": item.meta.nombre,
            "estado_meta": item.meta.estado,
            "indicador": item.nombre,
            "unidad_medida": item.unidad_medida,
            "valor_base": item.valor_base,
            "valor_meta": item.valor_meta,
            "valor_actual": item.valor_actual,
            "frecuencia": item.frecuencia,
            "activo": item.activo,
            "validado": item.validado,
        }


def avances(usuario, filtros):
    planes_visibles = _filtrar_planes_base(Plan.objects.all(), usuario)
    queryset = AvanceIndicador.objects.select_related(
        "indicador", "indicador__meta", "indicador__meta__plan",
        "indicador__meta__plan__entidad", "registrado_por",
    ).filter(indicador__meta__plan__in=planes_visibles)
    queryset = _aplicar_filtro_entidad(
        queryset, filtros, "indicador__meta__plan__entidad"
    )
    if filtros.get("fecha_desde"):
        queryset = queryset.filter(fecha_registro__gte=filtros["fecha_desde"])
    if filtros.get("fecha_hasta"):
        queryset = queryset.filter(fecha_registro__lte=filtros["fecha_hasta"])
    queryset = _filtrar_por_texto(
        queryset,
        filtros.get("buscar"),
        ("indicador__nombre", "indicador__meta__nombre", "indicador__meta__plan__nombre"),
    )
    for item in queryset.order_by("-fecha_registro", "-id")[: filtros["limite"]]:
        plan = item.indicador.meta.plan
        yield {
            "entidad": plan.entidad.nombre if plan.entidad else "",
            "plan": plan.nombre,
            "meta": item.indicador.meta.nombre,
            "indicador": item.indicador.nombre,
            "fecha_registro": item.fecha_registro,
            "valor": item.valor,
            "observacion": item.observacion,
            "registrado_por": _texto_usuario(item.registrado_por),
        }


def alineacion(usuario, filtros):
    queryset = Alineacion.objects.select_related(
        "objetivo_estrategico", "objetivo_estrategico__entidad",
        "objetivo_pnd", "objetivo_pnd__eje", "ods",
        "usuario_creador", "usuario_validador",
    )
    queryset = filtrar_queryset_por_entidad(
        queryset, usuario, "objetivo_estrategico__entidad"
    )
    queryset = _aplicar_filtro_entidad(
        queryset, filtros, "objetivo_estrategico__entidad"
    )
    if filtros.get("estado"):
        queryset = queryset.filter(estado=filtros["estado"])
    queryset = _filtrar_por_texto(
        queryset,
        filtros.get("buscar"),
        ("objetivo_estrategico__nombre", "objetivo_pnd__nombre", "ods__nombre"),
    )
    for item in queryset.order_by("-fecha_actualizacion")[: filtros["limite"]]:
        yield {
            "entidad": item.objetivo_estrategico.entidad.nombre,
            "objetivo_estrategico": (
                f"{item.objetivo_estrategico.codigo} - {item.objetivo_estrategico.nombre}"
            ),
            "eje_pnd": f"{item.objetivo_pnd.eje.codigo} - {item.objetivo_pnd.eje.nombre}",
            "objetivo_pnd": f"{item.objetivo_pnd.codigo} - {item.objetivo_pnd.nombre}",
            "ods": f"ODS {item.ods.numero} - {item.ods.nombre}",
            "justificacion": item.justificacion,
            "estado": item.estado,
            "creado_por": _texto_usuario(item.usuario_creador),
            "validado_por": _texto_usuario(item.usuario_validador),
        }


def proyectos(usuario, filtros):
    # Se replica la regla autorizativa del módulo sin depender de parámetros de cliente.
    queryset = ProyectoInversion.objects.select_related(
        "entidad",
        "plan",
        "objetivo_estrategico",
        "tipologia_intervencion",
        "responsable",
        "creado_por",
    )
    alcance = obtener_alcance_usuario(usuario)
    queryset = filtrar_queryset_por_entidad(queryset, usuario, "entidad")
    if alcance in {"ENTIDAD", "PROPIO_ASIGNADO"}:
        queryset = queryset.filter(Q(creado_por=usuario) | Q(responsable=usuario))
    queryset = _aplicar_filtro_entidad(queryset, filtros, "entidad")
    if filtros.get("estado"):
        queryset = queryset.filter(estado=filtros["estado"])
    if filtros.get("activo") is not None:
        queryset = queryset.filter(activo=filtros["activo"])
    if filtros.get("fecha_desde"):
        queryset = queryset.filter(fecha_inicio__gte=filtros["fecha_desde"])
    if filtros.get("fecha_hasta"):
        queryset = queryset.filter(fecha_fin__lte=filtros["fecha_hasta"])
    queryset = _filtrar_por_texto(
        queryset, filtros.get("buscar"), ("codigo", "nombre", "entidad__nombre")
    )
    for item in queryset.order_by("-fecha_creacion")[: filtros["limite"]]:
        yield {
            "codigo": item.codigo,
            "entidad": item.entidad.nombre,
            "plan": item.plan.nombre,
            "objetivo_estrategico": item.objetivo_estrategico.nombre,
            "nombre": item.nombre,
            "tipologia": item.tipologia_intervencion.nombre,
            "responsable": _texto_usuario(item.responsable),
            "fecha_inicio": item.fecha_inicio,
            "fecha_fin": item.fecha_fin,
            "presupuesto_estimado": item.presupuesto_estimado,
            "avance_fisico": item.avance_fisico,
            "avance_financiero": item.avance_financiero,
            "estado": item.estado,
        }


def auditoria(usuario, filtros):
    queryset = EventoAuditoria.objects.select_related("usuario", "entidad")
    queryset = filtrar_queryset_por_entidad(queryset, usuario, "entidad")
    queryset = _aplicar_filtro_entidad(queryset, filtros, "entidad")
    for clave in ("modulo", "accion", "resultado"):
        if filtros.get(clave):
            queryset = queryset.filter(**{clave: filtros[clave]})
    if filtros.get("fecha_desde"):
        queryset = queryset.filter(fecha_hora__date__gte=filtros["fecha_desde"])
    if filtros.get("fecha_hasta"):
        queryset = queryset.filter(fecha_hora__date__lte=filtros["fecha_hasta"])
    queryset = _filtrar_por_texto(
        queryset,
        filtros.get("buscar"),
        ("usuario_identificador", "funcionalidad", "tipo_entidad", "registro_id", "detalle"),
    )
    for item in queryset.order_by("-fecha_hora", "-id")[: filtros["limite"]]:
        yield {
            "fecha_hora": item.fecha_hora,
            "usuario": item.usuario_identificador,
            "entidad": item.entidad.nombre if item.entidad else "",
            "modulo": item.modulo,
            "funcionalidad": item.funcionalidad,
            "accion": item.accion,
            "tipo_entidad": item.tipo_entidad,
            "registro_id": item.registro_id,
            "resultado": item.resultado,
            "direccion_ip": item.direccion_ip or "",
            "detalle": item.detalle,
        }


DATASETS = {
    spec.codigo: spec
    for spec in (
        DatasetSpec(
            "usuarios-roles", "Usuarios y roles",
            "Usuarios, rol y adscripción institucional.",
            ("usuarios.ver", "roles.ver"),
            (("usuario", "Usuario"), ("nombre_completo", "Nombre completo"),
             ("correo", "Correo"), ("rol", "Rol"), ("entidad", "Entidad"),
             ("unidad", "Unidad"), ("estado", "Estado"), ("activo", "Activo")),
            usuarios_roles,
            filtros=("buscar", "estado", "activo", "entidad"),
        ),
        DatasetSpec(
            "planes", "Planes por estado e institución", "Planes institucionales.",
            ("planes.ver",),
            (("id", "ID"), ("entidad", "Entidad"), ("nombre", "Plan"),
             ("periodo_inicio", "Inicio"), ("periodo_fin", "Fin"),
             ("responsable", "Responsable"), ("estado", "Estado"), ("activo", "Activo")),
            planes,
            filtros=("buscar", "estado", "activo", "entidad"),
        ),
        DatasetSpec(
            "metas-indicadores", "Metas e indicadores", "Medición de metas institucionales.",
            ("metas.ver", "indicadores.ver"),
            (("entidad", "Entidad"), ("plan", "Plan"), ("meta", "Meta"),
             ("estado_meta", "Estado meta"), ("indicador", "Indicador"),
             ("unidad_medida", "Unidad"), ("valor_base", "Base"),
             ("valor_meta", "Valor meta"), ("valor_actual", "Actual"),
             ("frecuencia", "Frecuencia"), ("activo", "Activo"),
             ("validado", "Validado")),
            metas_indicadores,
            filtros=("buscar", "estado", "activo", "entidad"),
        ),
        DatasetSpec(
            "avances", "Avances", "Historial de avance de indicadores.",
            ("indicadores.ver",),
            (("entidad", "Entidad"), ("plan", "Plan"), ("meta", "Meta"),
             ("indicador", "Indicador"), ("fecha_registro", "Fecha"),
             ("valor", "Valor"), ("observacion", "Observación"),
             ("registrado_por", "Registrado por")),
            avances,
            filtros=("buscar", "entidad", "fecha_desde", "fecha_hasta"),
        ),
        DatasetSpec(
            "alineacion", "Alineación PND y ODS", "Matriz de alineación institucional.",
            ("objetivos.ver", "alineaciones.ver"),
            (("entidad", "Entidad"), ("objetivo_estrategico", "Objetivo estratégico"),
             ("eje_pnd", "Eje PND"), ("objetivo_pnd", "Objetivo PND"),
             ("ods", "ODS"), ("justificacion", "Justificación"),
             ("estado", "Estado"), ("creado_por", "Creado por"),
             ("validado_por", "Validado por")),
            alineacion,
            filtros=("buscar", "estado", "entidad"),
        ),
        DatasetSpec(
            "proyectos", "Proyectos", "Proyectos de inversión y sus avances.",
            ("proyectos.ver",),
            (("codigo", "Código"), ("entidad", "Entidad"), ("plan", "Plan"),
             ("objetivo_estrategico", "Objetivo"), ("nombre", "Proyecto"),
             ("tipologia", "Tipología"), ("responsable", "Responsable"),
             ("fecha_inicio", "Inicio"), ("fecha_fin", "Fin"),
             ("presupuesto_estimado", "Presupuesto"), ("avance_fisico", "Avance físico"),
             ("avance_financiero", "Avance financiero"), ("estado", "Estado")),
            proyectos,
            filtros=("buscar", "estado", "activo", "entidad", "fecha_desde", "fecha_hasta"),
        ),
        DatasetSpec(
            "auditoria", "Auditoría", "Trazabilidad de acciones del sistema.",
            ("auditoria.ver",),
            (("fecha_hora", "Fecha y hora"), ("usuario", "Usuario"),
             ("entidad", "Entidad"), ("modulo", "Módulo"),
             ("funcionalidad", "Funcionalidad"), ("accion", "Acción"),
             ("tipo_entidad", "Tipo de registro"), ("registro_id", "ID"),
             ("resultado", "Resultado"), ("direccion_ip", "Dirección IP"),
             ("detalle", "Detalle")),
            auditoria,
            filtros=("buscar", "entidad", "modulo", "accion", "resultado", "fecha_desde", "fecha_hasta"),
            permisos_exportacion=("auditoria.exportar",),
        ),
    )
}


def valor_json(valor):
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return str(valor)
    return valor
