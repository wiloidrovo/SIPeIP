import { ResourcePage } from "../../components/ResourcePage";

export function AvancesPage() {
  // Historial de consulta. Las mediciones se registran desde su indicador para
  // que el backend actualice también el valor actual y tome el autor de la sesión.
  return <ResourcePage eyebrow="Seguimiento" title="Avances de indicadores" description="Consulte las mediciones registradas para cada indicador." apiPath="/avances-indicadores/" viewPermission="indicadores.ver" columns={[
    { key: "fecha_registro", label: "Fecha" }, { key: "indicador_detalle.nombre", label: "Indicador" }, { key: "indicador_detalle.meta", label: "Meta" }, { key: "valor", label: "Valor" }, { key: "observacion", label: "Observación" }, { key: "registrado_por_detalle.nombre_completo", label: "Registrado por" },
  ]} />;
}
