import { ResourcePage, optionsFrom } from "../../components/ResourcePage";
import type {
  SelectFilterContext,
  SelectOption,
} from "../../components/ResourcePage";

const entityOptions = optionsFrom(
  "/configuracion/entidades/",
  (item) => `${String(item.codigo_oficial)} · ${String(item.nombre)}`,
  (item) => String(item.estado) !== "ACTIVA",
);
const unitOptions = optionsFrom(
  "/configuracion/unidades/",
  (item) => String(item.nombre),
  (item) => String(item.estado) !== "ACTIVA",
);

function unitMatchesSelectedEntity(
  option: SelectOption,
  context: SelectFilterContext,
) {
  if (context.editing && String(option.value) === String(context.editing.id)) {
    return false;
  }
  const entityId = String(context.values.entidad ?? "");
  const optionEntity = option.record?.entidad;
  return Boolean(entityId && String(optionEntity ?? "") === entityId);
}

export function UnidadesPage() {
  return <ResourcePage eyebrow="Configuración institucional" title="Unidades organizacionales" description="Organice las unidades y sus dependencias dentro de cada entidad." apiPath="/configuracion/unidades/" viewPermission="configuracion.ver" createPermission="configuracion.gestionar" editPermission="configuracion.gestionar" fields={[
    {
      name: "entidad",
      label: "Entidad",
      type: "select",
      required: true,
      loadOptions: entityOptions,
      emptyOptionsMessage: "No hay entidades activas dentro de su ámbito.",
    },
    { name: "nombre", label: "Nombre", required: true },
    { name: "codigo", label: "Código opcional" },
    {
      name: "unidad_padre",
      label: "Unidad superior",
      type: "select",
      emptyAsNull: true,
      loadOptions: unitOptions,
      filterOptions: unitMatchesSelectedEntity,
      dependsOn: ["entidad"],
      emptyOptionsMessage: (context) => context.values.entidad
        ? "La entidad seleccionada todavía no tiene otra unidad activa."
        : "Seleccione primero una entidad.",
    },
  ]} columns={[
    { key: "codigo", label: "Código" }, { key: "nombre", label: "Unidad" }, { key: "entidad_detalle.nombre", label: "Entidad" }, { key: "unidad_padre_detalle.nombre", label: "Depende de" }, { key: "subunidades_count", label: "Subunidades" }, { key: "estado", label: "Estado" },
  ]} actions={[
    { key: "activar", label: "Activar", permission: "configuracion.gestionar", states: ["INACTIVA"], tone: "success" },
    { key: "desactivar", label: "Desactivar", permission: "configuracion.gestionar", states: ["ACTIVA"], tone: "danger", confirm: "La unidad quedará inactiva y no podrá usarse en nuevas asignaciones." },
  ]} />;
}
