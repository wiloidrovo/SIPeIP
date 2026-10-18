from rest_framework.routers import DefaultRouter

from .views import EventoAuditoriaViewSet


# Publica /api/auditoria/eventos/ y el detalle de cada evento, solo de lectura.
router = DefaultRouter()
router.register("eventos", EventoAuditoriaViewSet, basename="auditoria-eventos")

urlpatterns = router.urls
