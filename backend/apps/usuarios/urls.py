from rest_framework.routers import DefaultRouter

from .views import UsuarioViewSet

# config/urls.py aporta /api/usuarios/. Las acciones de estado se publican
# junto al CRUD, pero requieren los permisos definidos en UsuarioViewSet.
router = DefaultRouter()
router.register("", UsuarioViewSet, basename="usuarios")

urlpatterns = router.urls
