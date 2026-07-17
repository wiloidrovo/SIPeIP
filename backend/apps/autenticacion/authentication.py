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

        return super().authenticate(request)

    def authenticate_header(self, request):
        return "Session"
