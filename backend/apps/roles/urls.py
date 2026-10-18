from rest_framework.routers import DefaultRouter

from .views import RolViewSet

# config/urls.py aporta /api/roles/; el router añade listado, detalle y
# acciones específicas de permisos, alcance y estado.
router = DefaultRouter()
router.register("", RolViewSet, basename="roles")

urlpatterns = router.urls
