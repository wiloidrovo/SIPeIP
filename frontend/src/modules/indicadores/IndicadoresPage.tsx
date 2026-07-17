import { ResourcePage, optionsFrom } from "../../components/ResourcePage";

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

export function IndicadoresPage() {
  return <ResourcePage eyebrow="Seguimiento" title="Indicadores" description="Configure métricas, registre avances y valide los indicadores institucionales." apiPath="/indicadores/" viewPermission="indicadores.ver" createPermission="indicadores.crear" editPermission="indicadores.editar" deletePermission="indicadores.eliminar" initialValues={{ valor_base: "0.00", frecuencia: "TRIMESTRAL" }} fields={[
    { name: "meta", label: "Meta", type: "select", required: true, loadOptions: metas },
    { name: "nombre", label: "Nombre", required: true }, { name: "descripcion", label: "Descripción", type: "textarea" },
    { name: "unidad_medida", label: "Unidad de medida", required: true },
    { name: "valor_base", label: "Valor base", type: "number", min: 0, step: "0.01", required: true },
    { name: "valor_meta", label: "Valor meta", type: "number", min: 0, step: "0.01", required: true },
    { name: "frecuencia", label: "Frecuencia", type: "select", required: true, options: frequencies },
  ]} columns={[
    { key: "nombre", label: "Indicador" }, { key: "meta_detalle.nombre", label: "Meta" }, { key: "unidad_medida", label: "Unidad" }, { key: "valor_actual", label: "Actual" }, { key: "valor_meta", label: "Meta" }, { key: "validado", label: "Validado" }, { key: "activo", label: "Activo" },
  ]} actions={[
    { key: "activar", label: "Activar", permission: "indicadores.editar", stateField: "activo", states: ["false"], tone: "success" },
    { key: "desactivar", label: "Desactivar", permission: "indicadores.editar", stateField: "activo", states: ["true"], tone: "danger", confirm: "El indicador dejará de aceptar nuevos avances." },
    { key: "validar", label: "Validar", permission: "indicadores.validar", stateField: "validado", states: ["false"], tone: "success", confirm: "Confirme que el indicador cumple los criterios institucionales.", canRun: (item) => item.activo === true },
    { key: "registrar-avance", label: "Registrar avance", permission: "indicadores.registrar_avance", stateField: "activo", states: ["true"], formFields: [
      { name: "fecha_registro", label: "Fecha de registro", type: "date", required: true },
      { name: "valor", label: "Valor alcanzado", type: "number", min: 0, step: "0.01", required: true },
      { name: "observacion", label: "Observación", type: "textarea" },
    ] },
  ]} canEdit={(item) => item.validado !== true} canDelete={(item) => Number(item.avances_count) === 0} />;
}
