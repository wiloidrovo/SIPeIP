from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.auditoria.services import registrar_evento

from .authentication import SipeipSessionAuthentication
from .serializers import LoginSerializer, UsuarioSesionSerializer


def _session_age_seconds():
    return int(getattr(settings, "AUTH_SESSION_AGE_SECONDS", 900))


def _renovar_expiracion(request):
    request.session.set_expiry(_session_age_seconds())


def _respuesta_sesion(usuario, detail):
    return {
        "detail": detail,
        "usuario": UsuarioSesionSerializer(usuario).data,
        "expira_en_segundos": _session_age_seconds(),
    }


@method_decorator(never_cache, name="dispatch")
@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "detail": "Token CSRF preparado correctamente.",
                "csrf_token": get_token(request._request),
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(never_cache, name="dispatch")
@method_decorator(sensitive_post_parameters("password"), name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usuario = authenticate(
            request=request._request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )

        if (
            usuario is None
            or not usuario.is_active
            or usuario.estado != usuario.EstadoUsuario.ACTIVO
        ):
            usuario_identificado = (
                get_user_model()
                .objects.select_related("entidad")
                .filter(username__iexact=serializer.validated_data["username"])
                .first()
            )
            registrar_evento(
                request=request,
                modulo="autenticacion",
                funcionalidad="inicio de sesión",
                accion="LOGIN",
                resultado="FALLO",
                detalle="Credenciales inválidas o cuenta no operativa.",
                identificador=serializer.validated_data["username"],
                entidad=(
                    usuario_identificado.entidad
                    if usuario_identificado is not None
                    else None
                ),
            )
            return Response(
                {"detail": "El usuario o la contraseña son incorrectos."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        django_login(request._request, usuario)
        _renovar_expiracion(request._request)
        registrar_evento(
            request=request,
            modulo="autenticacion",
            funcionalidad="inicio de sesión",
            accion="LOGIN",
            usuario=usuario,
        )

        return Response(
            _respuesta_sesion(usuario, "Inicio de sesión correcto."),
            status=status.HTTP_200_OK,
        )


@method_decorator(never_cache, name="dispatch")
class RefreshView(APIView):
    authentication_classes = [SipeipSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request._request.session.cycle_key()
        _renovar_expiracion(request._request)
        return Response(
            _respuesta_sesion(request.user, "Sesión renovada correctamente."),
            status=status.HTTP_200_OK,
        )


@method_decorator(never_cache, name="dispatch")
class LogoutView(APIView):
    authentication_classes = [SipeipSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        registrar_evento(
            request=request,
            modulo="autenticacion",
            funcionalidad="cierre de sesión",
            accion="LOGOUT",
            usuario=request.user,
        )
        django_logout(request._request)
        return Response(
            {"detail": "Sesión cerrada correctamente."},
            status=status.HTTP_200_OK,
        )


@method_decorator(never_cache, name="dispatch")
class MeView(APIView):
    authentication_classes = [SipeipSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            UsuarioSesionSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )
