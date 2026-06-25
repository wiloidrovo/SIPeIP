from rest_framework.routers import DefaultRouter

from .views import RolViewSet

router = DefaultRouter()
router.register("", RolViewSet, basename="roles")

urlpatterns = router.urls