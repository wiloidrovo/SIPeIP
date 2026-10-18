from rest_framework.routers import DefaultRouter

from .views import PlanViewSet

# El prefijo /api/planes/ ya se agrega en config/urls.py. La ruta vacía
# evita duplicarlo y el router incorpora las acciones de revisión del plan.
router = DefaultRouter()
router.register("", PlanViewSet, basename="planes")

urlpatterns = router.urls
