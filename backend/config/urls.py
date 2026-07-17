"""Enrutamiento principal de la API. Conecta las aplicaciones del sistema."""
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.autenticacion.urls")),
    path("api/dashboard/", include("apps.dashboard.urls")),
    path("api/roles/", include("apps.roles.urls")),
    path("api/usuarios/", include("apps.usuarios.urls")),
    path("api/configuracion/", include("apps.configuracion.urls")),
    path("api/planes/", include("apps.planes.urls")),
    path("api/", include("apps.metas.urls")),
    path("api/", include("apps.objetivos.urls")),
    path("api/", include("apps.proyectos.urls")),
    path("api/auditoria/", include("apps.auditoria.urls")),
    path("api/reportes/", include("apps.reportes.urls")),
]
