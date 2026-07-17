from rest_framework.routers import DefaultRouter

from .views import (
    AlineacionViewSet,
    EjePNDViewSet,
    ObjetivoEstrategicoViewSet,
    ObjetivoPNDViewSet,
    ODSViewSet,
)


router = DefaultRouter()
router.register(
    "objetivos-estrategicos",
    ObjetivoEstrategicoViewSet,
    basename="objetivos-estrategicos",
)
router.register("ejes-pnd", EjePNDViewSet, basename="ejes-pnd")
router.register("objetivos-pnd", ObjetivoPNDViewSet, basename="objetivos-pnd")
router.register("ods", ODSViewSet, basename="ods")
router.register("alineaciones", AlineacionViewSet, basename="alineaciones")

urlpatterns = router.urls
