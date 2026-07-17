from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditoria.services import registrar_evento

from .datasets import DATASETS, valor_json
from .exporters import EXPORTADORES, MIME_TYPES
from .permissions import PuedeGenerarReporte
from .serializers import FiltrosReporteSerializer


PARAMETROS_FILTRO = frozenset(FiltrosReporteSerializer().fields)


class CatalogoReportesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        permisos = request.user.get_sipeip_permissions()
        if "reportes.ver" not in permisos:
            return Response(
                {"detail": "No tiene permiso para consultar reportes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        resultados = []
        for spec in DATASETS.values():
            if all(codigo in permisos for codigo in spec.permisos_fuente):
                puede_exportar = (
                    "reportes.exportar" in permisos
                    and all(codigo in permisos for codigo in spec.permisos_exportacion)
                )
                resultados.append(
                    {
                        "codigo": spec.codigo,
                        "nombre": spec.nombre,
                        "descripcion": spec.descripcion,
                        "filtros": list(spec.filtros),
                        "formatos": list(EXPORTADORES) if puede_exportar else [],
                        "puede_generar": True,
                        "puede_exportar": puede_exportar,
                    }
                )
        return Response(resultados)


class ReporteBaseView(APIView):
    permission_classes = [IsAuthenticated, PuedeGenerarReporte]

    def get_dataset_spec(self, request):
        return DATASETS.get(self.kwargs.get("codigo"))

    def _obtener_filtros(self, request):
        desconocidos = set(request.query_params) - PARAMETROS_FILTRO
        if desconocidos:
            return None, Response(
                {
                    "detail": "Se recibieron filtros no reconocidos.",
                    "filtros": sorted(desconocidos),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Un QueryDict se interpreta como formulario HTML y DRF asigna False a
        # booleanos ausentes. Convertirlo evita aplicar `activo=False` cuando el
        # cliente no envió ese filtro.
        serializer = FiltrosReporteSerializer(data=request.query_params.dict())
        if not serializer.is_valid():
            return None, Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return serializer.validated_data, None

    def _generar(self, request):
        spec = self.get_dataset_spec(request)
        if spec is None:
            return None, None, Response(
                {"detail": "El reporte solicitado no existe."},
                status=status.HTTP_404_NOT_FOUND,
            )
        filtros, error = self._obtener_filtros(request)
        if error is not None:
            return None, None, error
        filas = list(spec.constructor(request.user, filtros))
        metadata = {
            "reporte": spec.codigo,
            "nombre": spec.nombre,
            "generado_en": timezone.localtime().isoformat(),
            "total": len(filas),
            "filtros": {
                clave: valor_json(valor)
                for clave, valor in filtros.items()
                if clave != "limite"
            },
            "limite": filtros["limite"],
        }
        return spec, (filas, metadata), None

    def _auditar(self, request, spec, metadata, formato):
        registrar_evento(
            request=request,
            modulo="reportes",
            funcionalidad=spec.nombre,
            accion=("EXPORTAR" if formato else "GENERAR"),
            resultado="EXITO",
            detalle=(
                f"Reporte {spec.codigo}; formato {formato or 'vista previa'}; "
                f"registros {metadata['total']}."
            ),
        )


class GenerarReporteView(ReporteBaseView):
    required_report_permission = "reportes.ver"

    def get(self, request, codigo):
        spec, generado, error = self._generar(request)
        if error is not None:
            return error
        filas, metadata = generado
        self._auditar(request, spec, metadata, None)
        return Response(
            {
                **metadata,
                "columnas": [
                    {"campo": campo, "titulo": titulo}
                    for campo, titulo in spec.columnas
                ],
                "resultados": [
                    {clave: valor_json(valor) for clave, valor in fila.items()}
                    for fila in filas
                ],
            }
        )


class ExportarReporteView(ReporteBaseView):
    required_report_permission = "reportes.exportar"

    def get(self, request, codigo, formato):
        exportador = EXPORTADORES.get(formato)
        if exportador is None:
            return Response(
                {"detail": "El formato solicitado no está disponible."},
                status=status.HTTP_404_NOT_FOUND,
            )
        spec, generado, error = self._generar(request)
        if error is not None:
            return error
        filas, metadata = generado
        contenido = exportador(spec, filas, metadata)
        respuesta = HttpResponse(contenido, content_type=MIME_TYPES[formato])
        respuesta["Content-Disposition"] = (
            f'attachment; filename="sipeip-{spec.codigo}.{formato}"'
        )
        respuesta["X-Content-Type-Options"] = "nosniff"
        self._auditar(request, spec, metadata, formato)
        return respuesta
