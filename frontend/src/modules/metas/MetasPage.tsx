import { Link } from "react-router-dom";
import { ResourcePage, optionsFrom } from "../../components/ResourcePage";
import type {
  SelectFilterContext,
  SelectOption,
} from "../../components/ResourcePage";
import { OdsBadges, TrackingStatus } from "../../components/TrackingStatus";
import type { ApiRecord } from "../../services/api";

const editablePlanStates = new Set(["BORRADOR", "DEVUELTO", "RECHAZADO"]);

function asRecord(value: unknown) {
  return value && typeof value === "object"
    ? (value as Record<string, unknown>)
    : null;
}

function entityContext(value: unknown) {
  const entity = asRecord(value);
  if (!entity) return "Entidad sin detalle";
  const code = String(entity.codigo_oficial ?? "").trim();
  const name = String(entity.nombre ?? "").trim();
  return [code, name].filter(Boolean).join(" · ") || "Entidad sin detalle";
}

function optionEntityId(option: SelectOption) {
  const record = option.record;
  const directEntity = record?.entidad;
  if (typeof directEntity === "number" || typeof directEntity === "string") {
    return String(directEntity);
  }
  const detail = asRecord(record?.entidad_detalle);
  return detail?.id === undefined ? "" : String(detail.id);
}

function selectedOption(
  fieldName: string,
  context: SelectFilterContext,
) {
  const selectedValue = String(context.values[fieldName] ?? "");
  return (context.options[fieldName] ?? []).find(
    (option) => String(option.value) === selectedValue,
  );
}

function objectiveMatchesSelectedPlan(
  option: SelectOption,
  context: SelectFilterContext,
) {
  const selectedPlan = selectedOption("plan", context);
  return Boolean(
    selectedPlan
    && optionEntityId(selectedPlan)
    && optionEntityId(selectedPlan) === optionEntityId(option),
  );
}

const plans = optionsFrom(
  "/planes/",
  (item) => `${String(item.nombre)} — ${entityContext(item.entidad_detalle)}`,
  (item) => item.activo === false || !editablePlanStates.has(String(item.estado)),
);
const strategicObjectives = optionsFrom(
  "/objetivos-estrategicos/",
  (item) => {
    const code = String(item.codigo ?? "").trim();
    const name = String(item.nombre ?? "").trim();
    return `${[code, name].filter(Boolean).join(" · ")} — ${entityContext(item.entidad_detalle)}`;
  },
  (item) => String(item.estado) !== "ACTIVO",
);

function planIsEditable(item: ApiRecord) {
  const detail = item.plan_detalle;
  if (!detail || typeof detail !== "object") return false;
  return editablePlanStates.has(
    String((detail as Record<string, unknown>).estado),
  );
}

function planIsApproved(item: ApiRecord) {
  const detail = asRecord(item.plan_detalle);
  return String(detail?.estado) === "APROBADO";
}

function goalIsExpired(item: ApiRecord) {
  const endDate = String(item.fecha_fin ?? "").slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(endDate)) return false;
  const today = new Date();
  const localToday = [
    today.getFullYear(),
    String(today.getMonth() + 1).padStart(2, "0"),
    String(today.getDate()).padStart(2, "0"),
  ].join("-");
  return endDate < localToday;
}

function objectiveIsActive(item: ApiRecord) {
  const detail = asRecord(item.objetivo_estrategico_detalle);
  return String(detail?.estado) === "ACTIVO";
}

export function MetasPage() {
  return (
    <ResourcePage
      eyebrow="Planificación"
      title="Metas institucionales"
      description="Defina resultados medibles dentro de un plan y vincule cada meta con el objetivo estratégico al que contribuye."
      apiPath="/metas/"
      viewPermission="metas.ver"
      createPermission="metas.crear"
      editPermission="metas.editar"
      deletePermission="metas.eliminar"
      fields={[
        {
          name: "plan",
          label: "Plan institucional",
          type: "select",
          required: true,
          loadOptions: plans,
          helpText: "Solo puede seleccionar planes en Borrador, Devuelto o Rechazado.",
          emptyOptionsMessage: "No hay planes editables disponibles.",
        },
        {
          name: "objetivo_estrategico",
          label: "Objetivo estratégico al que contribuye",
          type: "select",
          required: true,
          loadOptions: strategicObjectives,
          filterOptions: objectiveMatchesSelectedPlan,
          dependsOn: ["plan"],
          emptyOptionsMessage: (context) => context.values.plan
            ? "No hay objetivos activos para la entidad del plan."
            : "Seleccione primero un plan editable.",
        },
        { name: "nombre", label: "Nombre", required: true },
        { name: "descripcion", label: "Descripción", type: "textarea" },
        { name: "resultado_esperado", label: "Resultado esperado", type: "textarea" },
        { name: "fecha_inicio", label: "Fecha de inicio", type: "date", required: true },
        { name: "fecha_fin", label: "Fecha de fin", type: "date", required: true },
      ]}
      columns={[
        { key: "nombre", label: "Meta" },
        {
          key: "plan_detalle.nombre",
          label: "Plan / entidad",
          render: (item) => {
            const plan = asRecord(item.plan_detalle);
            const planId = plan?.id;
            return (
              <span>
                {planId ? (
                  <Link className="table-primary-link" to={`/planes/${String(planId)}`}>
                    {String(plan?.nombre ?? "Sin plan")}
                  </Link>
                ) : String(plan?.nombre ?? "Sin plan")}
                <small className="table-detail">{entityContext(plan?.entidad)}</small>
              </span>
            );
          },
        },
        {
          key: "objetivo_estrategico_detalle.nombre",
          label: "Objetivo estratégico",
          render: (item) => {
            const objective = asRecord(item.objetivo_estrategico_detalle);
            const code = String(objective?.codigo ?? "").trim();
            const name = String(objective?.nombre ?? "Sin objetivo");
            return (
              <span>
                {[code, name].filter(Boolean).join(" · ")}
                <small className="table-detail">{entityContext(objective?.entidad)}</small>
              </span>
            );
          },
        },
        { key: "resultado_esperado", label: "Resultado esperado" },
        { key: "fecha_fin", label: "Vencimiento" },
        { key: "indicadores_count", label: "Indicadores" },
        {
          key: "progreso",
          label: "Cumplimiento",
          render: (item) => (
            <TrackingStatus
              compact
              progress={item.progreso}
              status={String(item.estado_seguimiento ?? "")}
              label={typeof item.etiqueta_estado_seguimiento === "string" ? item.etiqueta_estado_seguimiento : undefined}
            />
          ),
        },
        {
          key: "alineaciones",
          label: "ODS",
          render: (item) => {
            const objective = asRecord(item.objetivo_estrategico_detalle);
            return (
              <OdsBadges
                value={
                  item.alineaciones
                  ?? item.ods_resumen
                  ?? item.ods
                  ?? objective?.alineaciones
                  ?? []
                }
              />
            );
          },
        },
        { key: "estado", label: "Estado" },
      ]}
      actions={[
        { key: "activar", label: "Activar", permission: "metas.editar", states: ["BORRADOR"], tone: "success", confirm: "La meta quedará activa para el seguimiento.", canRun: (item) => planIsEditable(item) && objectiveIsActive(item) },
        { key: "cerrar", label: "Cerrar", permission: "metas.editar", states: ["ACTIVA"], confirm: "La meta quedará cerrada y no admitirá edición ordinaria.", canRun: (item) => planIsApproved(item) && (Number(item.progreso) >= 100 || goalIsExpired(item)) },
        { key: "archivar", label: "Archivar", permission: "metas.archivar", states: ["BORRADOR", "ACTIVA", "CERRADA"], tone: "danger", confirm: "La meta y su historial se conservarán como registro archivado.", canRun: planIsEditable },
      ]}
      extraContent={(
        <section className="panel dashboard-guidance" aria-label="Relación entre metas y objetivos">
          <div>
            <span className="eyebrow">Cadena de planificación</span>
            <h2>Meta → Objetivo estratégico → PND / ODS</h2>
            <p>La meta concreta un resultado del plan. Su objetivo estratégico determina después cómo se vincula ese resultado con la planificación nacional y los ODS.</p>
          </div>
        </section>
      )}
      canEdit={(item) => ["BORRADOR", "ACTIVA"].includes(String(item.estado)) && planIsEditable(item)}
      canDelete={(item) => String(item.estado) === "BORRADOR" && Number(item.indicadores_count) === 0 && planIsEditable(item)}
    />
  );
}
