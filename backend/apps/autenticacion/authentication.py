from rest_framework.authentication import SessionAuthentication


class SipeipSessionAuthentication(SessionAuthentication):
    """Autenticación de sesión con CSRF y semántica HTTP 401 para la API."""

    def authenticate(self, request):
        usuario = getattr(request._request, "user", None)

        if (
            usuario is None
            or not usuario.is_active
            or getattr(usuario, "estado", None) != usuario.EstadoUsuario.ACTIVO
        ):
            return None

        # Mantiene la comprobación CSRF de SessionAuthentication para escrituras.
        return super().authenticate(request)

    def authenticate_header(self, request):
        # DRF necesita esta cabecera para responder 401 y no convertirlo en 403.
        return "Session"
