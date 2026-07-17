"""Respuestas JSON controladas para errores de la API."""

import logging

from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


logger = logging.getLogger(__name__)


ERRORS_BY_STATUS = {
    status.HTTP_401_UNAUTHORIZED: (
        "not_authenticated",
        "Se requiere autenticación válida.",
    ),
    status.HTTP_403_FORBIDDEN: (
        "permission_denied",
        "No tiene permiso para realizar esta acción.",
    ),
    status.HTTP_404_NOT_FOUND: (
        "not_found",
        "El recurso solicitado no existe.",
    ),
    status.HTTP_405_METHOD_NOT_ALLOWED: (
        "method_not_allowed",
        "El método solicitado no está permitido.",
    ),
    status.HTTP_429_TOO_MANY_REQUESTS: (
        "throttled",
        "Demasiados intentos. Espere antes de intentarlo nuevamente.",
    ),
}


def csrf_failure(request, reason=""):
    """Devuelve JSON estable cuando Django rechaza una solicitud por CSRF."""

    return JsonResponse(
        {
            "code": "csrf_failed",
            "detail": (
                "La verificación CSRF falló. Renueve el token e intente nuevamente."
            ),
        },
        status=status.HTTP_403_FORBIDDEN,
    )


def sipeip_exception_handler(exc, context):
    """Evita respuestas HTML y normaliza errores HTTP comunes en español."""

    response = exception_handler(exc, context)

    if response is None:
        logger.error(
            "Error no controlado al procesar una solicitud de la API.",
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return Response(
            {
                "code": "internal_error",
                "detail": "Ocurrió un error interno al procesar la solicitud.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if response.status_code == status.HTTP_403_FORBIDDEN and "csrf failed" in str(
        exc
    ).lower():
        response.data = {
            "code": "csrf_failed",
            "detail": "La verificación CSRF falló. Renueve el token e intente nuevamente.",
        }
        return response

    error = ERRORS_BY_STATUS.get(response.status_code)
    if error:
        code, message = error
        response.data = {"code": code, "detail": message}

    return response
