from rest_framework.routers import DefaultRouter

from .views import (
    HitoProyectoViewSet,
    ProyectoInversionViewSet,
    SeguimientoProyectoViewSet,
    TipologiaIntervencionViewSet,
)


# Expone proyecto, catálogo, cronograma y seguimiento como recursos
# separados, todos sujetos a los permisos y al alcance de sus vistas.
router = DefaultRouter()
router.register(
    "tipologias-intervencion",
    TipologiaIntervencionViewSet,
    basename="tipologias-intervencion",
)
router.register("proyectos", ProyectoInversionViewSet, basename="proyectos")
router.register("hitos-proyectos", HitoProyectoViewSet, basename="hitos-proyectos")
router.register(
    "seguimientos-proyectos",
    SeguimientoProyectoViewSet,
    basename="seguimientos-proyectos",
)

urlpatterns = router.urls
