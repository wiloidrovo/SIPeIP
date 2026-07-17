from rest_framework.routers import DefaultRouter

from .views import EntidadInstitucionalViewSet, UnidadOrganizacionalViewSet


router = DefaultRouter()
router.register("entidades", EntidadInstitucionalViewSet, basename="entidades")
router.register("unidades", UnidadOrganizacionalViewSet, basename="unidades")

urlpatterns = router.urls
