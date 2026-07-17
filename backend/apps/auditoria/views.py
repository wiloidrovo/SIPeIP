from rest_framework import filters, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from django.utils.dateparse import parse_date

from apps.configuracion.scope import filtrar_queryset_por_entidad
from apps.roles.permissions import HasSipeipPermission

from .models import EventoAuditoria
from .serializers import EventoAuditoriaSerializer


class EventoAuditoriaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EventoAuditoriaSerializer
    permission_classes = [IsAuthenticated, HasSipeipPermission]
    permission_map = {
        "list": "auditoria.ver",
        "retrieve": "auditoria.ver",
    }
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "usuario_identificador",
        "modulo",
        "funcionalidad",
        "accion",
        "tipo_entidad",
        "registro_id",
        "detalle",
        "resultado",
    ]
    ordering_fields = ["id", "fecha_hora", "modulo", "accion", "resultado"]
    ordering = ["-fecha_hora", "-id"]

    def get_queryset(self):
        queryset = EventoAuditoria.objects.select_related("usuario", "entidad")
        queryset = filtrar_queryset_por_entidad(
            queryset, self.request.user, "entidad"
        )
        filtros_exactos = {
            "modulo": "modulo",
            "accion": "accion",
            "resultado": "resultado",
            "entidad": "entidad_id",
            "usuario": "usuario_identificador",
        }
        for parametro, campo in filtros_exactos.items():
            valor = self.request.query_params.get(parametro)
            if valor:
                queryset = queryset.filter(**{campo: valor})
        fecha_desde = self.request.query_params.get("fecha_desde")
        fecha_hasta = self.request.query_params.get("fecha_hasta")
        if fecha_desde:
            fecha = parse_date(fecha_desde)
            if fecha is None:
                raise ValidationError({"fecha_desde": "Ingrese una fecha válida."})
            queryset = queryset.filter(fecha_hora__date__gte=fecha)
        if fecha_hasta:
            fecha = parse_date(fecha_hasta)
            if fecha is None:
                raise ValidationError({"fecha_hasta": "Ingrese una fecha válida."})
            queryset = queryset.filter(fecha_hora__date__lte=fecha)
        return queryset
