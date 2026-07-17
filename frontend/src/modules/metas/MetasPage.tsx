import { ResourcePage, optionsFrom } from "../../components/ResourcePage";
import type { ApiRecord } from "../../services/api";

const editablePlanStates = new Set(["BORRADOR", "DEVUELTO", "RECHAZADO"]);
const plans = optionsFrom(
  "/planes/",
  (item) => String(item.nombre),
  (item) => item.activo === false || !editablePlanStates.has(String(item.estado)),
);

function planIsEditable(item: ApiRecord) {
  const detail = item.plan_detalle;
  if (!detail || typeof detail !== "object") return false;
  return editablePlanStates.has(
    String((detail as Record<string, unknown>).estado),
  );
}

export function MetasPage() {
  return <ResourcePage eyebrow="Planificación" title="Metas institucionales" description="Defina resultados y periodos dentro de planes visibles; el ciclo de vida se controla mediante acciones específicas." apiPath="/metas/" viewPermission="metas.ver" createPermission="metas.crear" editPermission="metas.editar" deletePermission="metas.eliminar" fields={[
    { name: "plan", label: "Plan", type: "select", required: true, loadOptions: plans },
    { name: "nombre", label: "Nombre", required: true }, { name: "descripcion", label: "Descripción", type: "textarea" },
    { name: "resultado_esperado", label: "Resultado esperado", type: "textarea" },
    { name: "fecha_inicio", label: "Fecha de inicio", type: "date", required: true }, { name: "fecha_fin", label: "Fecha de fin", type: "date", required: true },
  ]} columns={[
    { key: "nombre", label: "Meta" }, { key: "plan_detalle.nombre", label: "Plan" }, { key: "resultado_esperado", label: "Resultado esperado" }, { key: "fecha_fin", label: "Vencimiento" }, { key: "indicadores_count", label: "Indicadores" }, { key: "estado", label: "Estado" },
  ]} actions={[
    { key: "activar", label: "Activar", permission: "metas.editar", states: ["BORRADOR"], tone: "success", confirm: "La meta quedará activa para el seguimiento.", canRun: planIsEditable },
    { key: "cerrar", label: "Cerrar", permission: "metas.editar", states: ["ACTIVA"], confirm: "La meta quedará cerrada y no admitirá edición ordinaria." },
    { key: "archivar", label: "Archivar", permission: "metas.archivar", states: ["BORRADOR", "ACTIVA", "CERRADA"], tone: "danger", confirm: "La meta y su historial se conservarán como registro archivado." },
  ]} canEdit={(item) => ["BORRADOR", "ACTIVA"].includes(String(item.estado)) && planIsEditable(item)} canDelete={(item) => String(item.estado) === "BORRADOR" && Number(item.indicadores_count) === 0 && planIsEditable(item)} />;
}
