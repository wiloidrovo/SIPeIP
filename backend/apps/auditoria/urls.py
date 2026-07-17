from rest_framework.routers import DefaultRouter

from .views import EventoAuditoriaViewSet


router = DefaultRouter()
router.register("eventos", EventoAuditoriaViewSet, basename="auditoria-eventos")

urlpatterns = router.urls
