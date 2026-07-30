import { Link } from "react-router-dom";
import { ResourcePage, optionsFrom } from "../../components/ResourcePage";
import { OdsBadges, TrackingStatus } from "../../components/TrackingStatus";

function asRecord(value: unknown) {
  return value && typeof value === "object"
    ? value as Record<string, unknown>
    : null;
}

function canRegisterProgress(item: Record<string, unknown>) {
  const meta = asRecord(item.meta_detalle);
  return item.activo === true
    && item.validado === true
    && String(meta?.plan_estado ?? "") === "APROBADO";
}

const editablePlanStates = new Set(["BORRADOR", "DEVUELTO", "RECHAZADO"]);
const metas = optionsFrom(
  "/metas/",
  (item) => String(item.nombre),
  (item) => {
    const plan = item.plan_detalle;
    const planState = plan && typeof plan === "object"
      ? String((plan as Record<string, unknown>).estado)
      : "";
    return item.activa !== true
      || String(item.estado) !== "ACTIVA"
      || !editablePlanStates.has(planState);
  },
);
const frequencies = ["MENSUAL", "TRIMESTRAL", "SEMESTRAL", "ANUAL"].map((value) => ({ value, label: value.charAt(0) + value.slice(1).toLowerCase() }));
const directions = [
  { value: "ASCENDENTE", label: "Ascendente: aumentar hasta la meta" },
  { value: "DESCENDENTE", label: "Descendente: reducir hasta la meta" },
];

export function IndicadoresPage() {
  return <ResourcePage eyebrow="Seguimiento" title="Indicadores" description="Configure métricas, registre avances y consulte cómo validan el cumplimiento de las metas." apiPath="/indicadores/" viewPermission="indicadores.ver" createPermission="indicadores.crear" editPermission="indicadores.editar" deletePermission="indicadores.eliminar" initialValues={{ valor_base: "0.00", frecuencia: "TRIMESTRAL", sentido: "ASCENDENTE", ponderacion: "100.00" }} fields={[
    {
      name: "meta",
      label: "Meta",
      type: "select",
      required: true,
      loadOptions: metas,
      helpText: "La meta debe estar activa y pertenecer a un plan editable.",
      emptyOptionsMessage: "No hay metas disponibles para registrar indicadores.",
    },
    { name: "nombre", label: "Nombre", required: true }, { name: "descripcion", label: "Descripción", type: "textarea" },
    { name: "unidad_medida", label: "Unidad de medida", required: true },
    { name: "valor_base", label: "Valor base", type: "number", min: 0, step: "0.01", required: true },
    { name: "valor_meta", label: "Valor meta", type: "number", min: 0, step: "0.01", required: true },
    { name: "frecuencia", label: "Frecuencia", type: "select", required: true, options: frequencies },
    { name: "sentido", label: "Sentido de medición", type: "select", required: true, options: directions, helpText: "Ascendente mide aumentos; descendente mide reducciones respecto de la línea base." },
    { name: "ponderacion", label: "Peso dentro de la meta (%)", type: "number", min: 0.01, max: 100, step: "0.01", required: true, helpText: "Los pesos de los indicadores activos de una meta deben sumar 100 %." },
  ]} columns={[
    {
      key: "nombre",
      label: "Indicador",
      render: (item) => (
        <span>
          <Link className="table-primary-link" to={`/indicadores/${item.id}`}>
            {String(item.nombre)}
          </Link>
          <small className="table-detail">Abrir seguimiento y mediciones</small>
        </span>
      ),
    },
    {
      key: "meta_detalle.nombre",
      label: "Meta / plan",
      render: (item) => {
        const meta = asRecord(item.meta_detalle);
        const plan = asRecord(meta?.plan_detalle);
        const planLabel = plan?.nombre ?? meta?.plan;
        return (
          <span>
            {String(meta?.nombre ?? "Sin meta")}
            <small className="table-detail">{String(planLabel ?? "Sin plan")}</small>
          </span>
        );
      },
    },
    { key: "unidad_medida", label: "Unidad" },
    {
      key: "valor_actual",
      label: "Medición",
      render: (item) => (
        <span>
          {String(item.valor_actual ?? "Sin dato")}
          <small className="table-detail">
            Base {String(item.valor_base ?? "—")} · Objetivo {String(item.valor_meta ?? "—")} · {String(item.sentido ?? "ASCENDENTE").toLocaleLowerCase("es-EC")}
          </small>
        </span>
      ),
    },
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
      key: "proxima_medicion",
      label: "Próxima medición",
      render: (item) => item.proxima_medicion
        ? new Date(`${String(item.proxima_medicion)}T00:00:00`).toLocaleDateString("es-EC")
        : <span className="muted">Sin fecha</span>,
    },
    {
      key: "alineaciones",
      label: "ODS",
      render: (item) => {
        const meta = asRecord(item.meta_detalle);
        return (
          <OdsBadges
            value={item.alineaciones ?? item.ods ?? meta?.alineaciones ?? []}
          />
        );
      },
    },
    { key: "validado", label: "Ficha validada" },
    { key: "activo", label: "Activo" },
  ]} actions={[
    { key: "activar", label: "Activar", permission: "indicadores.editar", stateField: "activo", states: ["false"], tone: "success" },
    { key: "desactivar", label: "Desactivar", permission: "indicadores.editar", stateField: "activo", states: ["true"], tone: "danger", confirm: "El indicador dejará de aceptar nuevos avances." },
    { key: "registrar-avance", label: "Registrar avance", permission: "indicadores.registrar_avance", stateField: "activo", states: ["true"], canRun: canRegisterProgress, formFields: [
      { name: "fecha_registro", label: "Fecha de registro", type: "date", required: true },
      { name: "valor", label: "Valor alcanzado", type: "number", min: 0, step: "0.01", required: true },
      { name: "observacion", label: "Observación", type: "textarea" },
      { name: "evidencia", label: "Referencia de evidencia", placeholder: "Documento, enlace o referencia que sustenta la medición" },
    ] },
  ]} canEdit={(item) => item.validado !== true} canDelete={(item) => Number(item.avances_count) === 0} />;
}
