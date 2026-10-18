from django.urls import path

from .views import DashboardView


app_name = "dashboard"

# La ruta base devuelve únicamente los resúmenes autorizados para la sesión.
urlpatterns = [path("", DashboardView.as_view(), name="resumen")]
