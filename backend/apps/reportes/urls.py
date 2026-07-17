from django.urls import path

from .views import CatalogoReportesView, ExportarReporteView, GenerarReporteView


urlpatterns = [
    path("catalogo/", CatalogoReportesView.as_view(), name="reportes-catalogo"),
    path("generar/<slug:codigo>/", GenerarReporteView.as_view(), name="reportes-generar"),
    path(
        "exportar/<slug:codigo>/<slug:formato>/",
        ExportarReporteView.as_view(),
        name="reportes-exportar",
    ),
]
