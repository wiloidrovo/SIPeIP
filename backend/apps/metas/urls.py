from rest_framework.routers import DefaultRouter

from .views import AvanceIndicadorViewSet, IndicadorViewSet, MetaViewSet

router = DefaultRouter()
router.register("metas", MetaViewSet, basename="metas")
router.register("indicadores", IndicadorViewSet, basename="indicadores")
router.register(
    "avances-indicadores",
    AvanceIndicadorViewSet,
    basename="avances-indicadores",
)

urlpatterns = router.urls