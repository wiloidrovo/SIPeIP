from rest_framework.routers import DefaultRouter

from .views import EntidadInstitucionalViewSet, UnidadOrganizacionalViewSet


# Agrupa entidades y unidades bajo el prefijo de configuración del proyecto.
router = DefaultRouter()
router.register("entidades", EntidadInstitucionalViewSet, basename="entidades")
router.register("unidades", UnidadOrganizacionalViewSet, basename="unidades")

urlpatterns = router.urls
