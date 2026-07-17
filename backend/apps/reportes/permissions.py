from rest_framework.permissions import BasePermission


class PuedeGenerarReporte(BasePermission):
    """Exige permisos de reportes y de cada fuente consultada."""

    message = "No tiene permiso para generar este reporte."

    def has_permission(self, request, view):
        usuario = request.user
        if not getattr(usuario, "is_authenticated", False):
            return False

        obtener_permisos = getattr(usuario, "get_sipeip_permissions", None)
        if obtener_permisos is None:
            return False
        permisos = obtener_permisos()

        permiso_operacion = getattr(view, "required_report_permission", None)
        if permiso_operacion not in permisos or "reportes.ver" not in permisos:
            return False

        especificacion = view.get_dataset_spec(request)
        if especificacion is None:
            return False
        requeridos = especificacion.permisos_fuente
        if permiso_operacion == "reportes.exportar":
            requeridos += especificacion.permisos_exportacion
        return all(codigo in permisos for codigo in requeridos)
