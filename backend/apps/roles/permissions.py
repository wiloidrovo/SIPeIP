"""Catálogo y autorización RBAC central de SIPeIP."""

from rest_framework.permissions import BasePermission


ALLOWED_ROLE_PERMISSIONS = (
    "usuarios.ver",
    "usuarios.crear",
    "usuarios.editar",
    "usuarios.eliminar",
    "roles.ver",
    "roles.crear",
    "roles.editar",
    "roles.eliminar",
    "roles.asignar_permisos",
    "planes.ver",
    "planes.crear",
    "planes.editar",
    "planes.eliminar",
    "planes.enviar_revision",
    "planes.revisar",
    "planes.devolver",
    "planes.aprobar",
    "planes.rechazar",
    "planes.archivar",
    "metas.ver",
    "metas.crear",
    "metas.editar",
    "metas.eliminar",
    "metas.archivar",
    "indicadores.ver",
    "indicadores.crear",
    "indicadores.editar",
    "indicadores.eliminar",
    "indicadores.registrar_avance",
    "indicadores.validar",
    "configuracion.ver",
    "configuracion.gestionar",
    "objetivos.ver",
    "objetivos.gestionar",
    "alineaciones.ver",
    "alineaciones.gestionar_catalogos",
    "alineaciones.gestionar",
    "alineaciones.validar",
    "proyectos.ver",
    "proyectos.crear",
    "proyectos.editar",
    "proyectos.eliminar",
    "proyectos.enviar_revision",
    "proyectos.devolver",
    "proyectos.aprobar",
    "proyectos.archivar",
    "proyectos.registrar_seguimiento",
    "proyectos.gestionar_catalogos",
    "reportes.ver",
    "reportes.exportar",
    "auditoria.ver",
    "auditoria.exportar",
)


def _permisos_ordenados(codigos):
    permitidos = set(codigos)
    return [codigo for codigo in ALLOWED_ROLE_PERMISSIONS if codigo in permitidos]


PERMISOS_USUARIOS = {
    codigo for codigo in ALLOWED_ROLE_PERMISSIONS if codigo.startswith("usuarios.")
}
PERMISOS_ROLES = {
    codigo for codigo in ALLOWED_ROLE_PERMISSIONS if codigo.startswith("roles.")
}


BASE_ROLES = {
    "administrador_sistema": {
        "nombre": "Administrador del Sistema",
        "descripcion": "Administra usuarios, roles y configuración institucional.",
        "alcance": "GLOBAL",
        "permisos": _permisos_ordenados(
            {
                *PERMISOS_USUARIOS,
                *PERMISOS_ROLES,
                "planes.ver",
                "metas.ver",
                "indicadores.ver",
                "configuracion.ver",
                "configuracion.gestionar",
                "objetivos.ver",
                "alineaciones.ver",
                "alineaciones.gestionar_catalogos",
                "proyectos.ver",
                "proyectos.gestionar_catalogos",
                "reportes.ver",
                "reportes.exportar",
                "auditoria.ver",
            }
        ),
    },
    "planificador_institucional": {
        "nombre": "Planificador Institucional",
        "descripcion": "Gestiona la planificación y el seguimiento institucional.",
        "alcance": "PROPIO_ASIGNADO",
        "permisos": _permisos_ordenados(
            {
                "usuarios.ver",
                "configuracion.ver",
                "planes.ver",
                "planes.crear",
                "planes.editar",
                "planes.enviar_revision",
                "planes.archivar",
                "metas.ver",
                "metas.crear",
                "metas.editar",
                "metas.archivar",
                "indicadores.ver",
                "indicadores.crear",
                "indicadores.editar",
                "indicadores.registrar_avance",
                "objetivos.ver",
                "objetivos.gestionar",
                "alineaciones.ver",
                "alineaciones.gestionar",
                "proyectos.ver",
                "proyectos.crear",
                "proyectos.editar",
                "proyectos.enviar_revision",
                "proyectos.archivar",
                "proyectos.registrar_seguimiento",
                "reportes.ver",
                "reportes.exportar",
            }
        ),
    },
    "supervisor_planificacion": {
        "nombre": "Supervisor de Planificación",
        "descripcion": "Revisa, devuelve, aprueba y rechaza planificación.",
        "alcance": "REVISION_ENTIDAD",
        "permisos": _permisos_ordenados(
            {
                "configuracion.ver",
                "planes.ver",
                "planes.revisar",
                "planes.devolver",
                "planes.aprobar",
                "planes.rechazar",
                "metas.ver",
                "indicadores.ver",
                "indicadores.validar",
                "objetivos.ver",
                "alineaciones.ver",
                "alineaciones.validar",
                "proyectos.ver",
                "proyectos.devolver",
                "proyectos.aprobar",
                "reportes.ver",
            }
        ),
    },
    "usuario_externo": {
        "nombre": "Usuario Externo",
        "descripcion": "Gestiona planificación propia dentro de su institución.",
        "alcance": "ENTIDAD",
        "permisos": _permisos_ordenados(
            {
                "configuracion.ver",
                "planes.ver",
                "planes.crear",
                "planes.editar",
                "planes.enviar_revision",
                "planes.archivar",
                "metas.ver",
                "metas.crear",
                "metas.editar",
                "metas.archivar",
                "indicadores.ver",
                "indicadores.crear",
                "indicadores.editar",
                "indicadores.registrar_avance",
                "objetivos.ver",
                "alineaciones.ver",
                "proyectos.ver",
                "proyectos.crear",
                "proyectos.editar",
                "proyectos.enviar_revision",
                "proyectos.archivar",
                "proyectos.registrar_seguimiento",
                "reportes.ver",
                "reportes.exportar",
            }
        ),
    },
    "auditor_control_interno": {
        "nombre": "Auditor / Control Interno",
        "descripcion": "Consulta trazabilidad y reportes sin mutaciones operativas.",
        "alcance": "LECTURA_ENTIDAD",
        "permisos": _permisos_ordenados(
            {
                "usuarios.ver",
                "roles.ver",
                "configuracion.ver",
                "planes.ver",
                "metas.ver",
                "indicadores.ver",
                "objetivos.ver",
                "alineaciones.ver",
                "proyectos.ver",
                "reportes.ver",
                "reportes.exportar",
                "auditoria.ver",
                "auditoria.exportar",
            }
        ),
    },
    "superadministrador_tecnico": {
        "nombre": "Superadministrador técnico",
        "descripcion": "Acceso técnico total y excepcional.",
        "alcance": "TOTAL",
        "permisos": list(ALLOWED_ROLE_PERMISSIONS),
    },
}

PROTECTED_ROLE_CODES = frozenset({"superadministrador_tecnico"})
SCOPE_RESTRICTED_ROLE_CODES = frozenset()

ALCANCES_DELEGABLES = {
    "TOTAL": frozenset(
        {
            "TOTAL",
            "GLOBAL",
            "ENTIDAD",
            "PROPIO_ASIGNADO",
            "REVISION_ENTIDAD",
            "LECTURA_ENTIDAD",
        }
    ),
    "GLOBAL": frozenset(
        {
            "GLOBAL",
            "ENTIDAD",
            "PROPIO_ASIGNADO",
            "REVISION_ENTIDAD",
            "LECTURA_ENTIDAD",
        }
    ),
    "ENTIDAD": frozenset({"ENTIDAD"}),
    "PROPIO_ASIGNADO": frozenset({"PROPIO_ASIGNADO"}),
    "REVISION_ENTIDAD": frozenset({"REVISION_ENTIDAD"}),
    "LECTURA_ENTIDAD": frozenset({"LECTURA_ENTIDAD"}),
}


def alcance_es_delegable(alcance_actor, alcance_destino):
    """Evita ampliar o alterar el ámbito institucional al delegar un rol."""

    return alcance_destino in ALCANCES_DELEGABLES.get(alcance_actor, frozenset())


def es_rol_tecnico_protegido(rol):
    """Identifica el rol técnico o un rol personalizado con acceso total."""

    permisos = getattr(rol, "permisos", [])
    return (
        getattr(rol, "codigo", None) in PROTECTED_ROLE_CODES
        or set(permisos) >= set(ALLOWED_ROLE_PERMISSIONS)
    )


class HasSipeipPermission(BasePermission):
    """Autoriza la acción DRF mediante un código explícito y deniega por defecto."""

    message = "No tiene permiso para realizar esta acción."

    def has_permission(self, request, view):
        usuario = request.user

        if not getattr(usuario, "is_authenticated", False):
            return False

        action = getattr(view, "action", None)
        permission_map = getattr(view, "permission_map", {})
        permiso_requerido = (
            permission_map.get(action)
            if action is not None
            else getattr(view, "required_permission", None)
        )

        if permiso_requerido not in ALLOWED_ROLE_PERMISSIONS:
            return False

        obtener_permisos = getattr(usuario, "get_sipeip_permissions", None)
        if obtener_permisos is None:
            return False

        return permiso_requerido in obtener_permisos()
