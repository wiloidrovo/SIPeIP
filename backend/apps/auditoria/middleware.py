import logging

from .services import registrar_evento


logger = logging.getLogger(__name__)

METODOS_MUTACION = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class AuditoriaFallosMiddleware:
    """Registra intentos fallidos sin inspeccionar ni persistir el payload."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            request.path.startswith("/api/")
            and request.method in METODOS_MUTACION
            and response.status_code >= 400
            and not getattr(request, "_sipeip_auditoria_registrada", False)
        ):
            self._registrar(request, response.status_code)
        return response

    @staticmethod
    def _registrar(request, status_code):
        try:
            segmentos = [item for item in request.path.split("/") if item]
            modulo = segmentos[1] if len(segmentos) > 1 else "api"
            resolver = getattr(request, "resolver_match", None)
            acciones = getattr(getattr(resolver, "func", None), "actions", {})
            accion = acciones.get(request.method.lower(), request.method)
            registrar_evento(
                request=request,
                modulo=modulo[:60],
                funcionalidad=request.path[:120],
                accion=str(accion).upper()[:60],
                resultado="FALLO",
                detalle=f"Solicitud rechazada con estado HTTP {status_code}.",
            )
        except Exception:
            logger.exception("No fue posible registrar un intento fallido en auditoría.")
