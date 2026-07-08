"""Enrutamiento principal de la API. Conecta las aplicaciones del sistema."""
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/roles/", include("apps.roles.urls")),
    path("api/usuarios/", include("apps.usuarios.urls")),
    path("api/planes/", include("apps.planes.urls")),
    path("api/", include("apps.metas.urls")),
]