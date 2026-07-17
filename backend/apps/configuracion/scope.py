"""Reglas centrales de alcance institucional con denegación por defecto."""

from django.core.exceptions import FieldError


ALCANCES_GLOBALES = frozenset({"TOTAL", "GLOBAL"})
ALCANCES_INSTITUCIONALES = frozenset(
    {"ENTIDAD", "PROPIO_ASIGNADO", "REVISION_ENTIDAD", "LECTURA_ENTIDAD"}
)
ALCANCES_RECONOCIDOS = ALCANCES_GLOBALES | ALCANCES_INSTITUCIONALES


def obtener_alcance_usuario(usuario):
    """Obtiene un alcance válido solo para una identidad operativa."""

    if not getattr(usuario, "is_authenticated", False):
        return None
    if not getattr(usuario, "is_active", False):
        return None
    if getattr(usuario, "estado", None) not in (None, "ACTIVO"):
        return None

    if getattr(usuario, "is_superuser", False):
        return "TOTAL"

    rol = getattr(usuario, "rol", None)
    if rol is None or not getattr(rol, "activo", False):
        return None

    alcance = getattr(rol, "alcance", None)
    if alcance not in ALCANCES_RECONOCIDOS:
        return None
    if alcance in ALCANCES_INSTITUCIONALES:
        entidad = getattr(usuario, "entidad", None)
        if entidad is None or getattr(entidad, "estado", None) != "ACTIVA":
            return None
    return alcance


def tiene_alcance_global(usuario):
    return obtener_alcance_usuario(usuario) in ALCANCES_GLOBALES


def usuario_puede_acceder_entidad(usuario, entidad_id):
    """Comprueba el límite de entidad sin depender del nombre del rol."""

    alcance = obtener_alcance_usuario(usuario)
    if alcance in ALCANCES_GLOBALES:
        return True
    if alcance not in ALCANCES_INSTITUCIONALES or entidad_id is None:
        return False
    return getattr(usuario, "entidad_id", None) == entidad_id


def filtrar_queryset_por_entidad(queryset, usuario, lookup="entidad"):
    """Aplica el límite institucional a cualquier queryset relacionado.

    ``lookup`` identifica la ruta hacia EntidadInstitucional. Puede ser un
    campo directo (``entidad``), una ruta relacional (``plan__entidad``) o
    ``pk``/``id`` cuando el queryset ya contiene entidades.

    Los alcances PROPIO_ASIGNADO y REVISION_ENTIDAD se limitan aquí a su
    institución; cada módulo debe estrechar además por propietario, asignación
    o estado cuando su flujo lo requiera.
    """

    alcance = obtener_alcance_usuario(usuario)
    if alcance in ALCANCES_GLOBALES:
        return queryset
    if alcance not in ALCANCES_INSTITUCIONALES:
        return queryset.none()

    entidad_id = getattr(usuario, "entidad_id", None)
    if entidad_id is None:
        return queryset.none()

    ruta = str(lookup or "").strip()
    if not ruta:
        return queryset.none()
    if ruta in {"pk", "id"} or ruta.endswith("_id"):
        campo = ruta
    else:
        campo = f"{ruta}_id"

    try:
        return queryset.filter(**{campo: entidad_id})
    except FieldError:
        # Un lookup mal configurado jamás debe ampliar el acceso.
        return queryset.none()
