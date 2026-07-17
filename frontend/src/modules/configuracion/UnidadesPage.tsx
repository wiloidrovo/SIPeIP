import { ResourcePage, optionsFrom } from "../../components/ResourcePage";

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

export function UnidadesPage() {
  return <ResourcePage eyebrow="Configuración institucional" title="Unidades organizacionales" description="Organice las unidades y sus dependencias dentro de cada entidad." apiPath="/configuracion/unidades/" viewPermission="configuracion.ver" createPermission="configuracion.gestionar" editPermission="configuracion.gestionar" fields={[
    { name: "entidad", label: "Entidad", type: "select", required: true, loadOptions: entityOptions },
    { name: "nombre", label: "Nombre", required: true },
    { name: "codigo", label: "Código opcional" },
    { name: "unidad_padre", label: "Unidad superior", type: "select", emptyAsNull: true, loadOptions: unitOptions },
  ]} columns={[
    { key: "codigo", label: "Código" }, { key: "nombre", label: "Unidad" }, { key: "entidad_detalle.nombre", label: "Entidad" }, { key: "unidad_padre_detalle.nombre", label: "Depende de" }, { key: "subunidades_count", label: "Subunidades" }, { key: "estado", label: "Estado" },
  ]} actions={[
    { key: "activar", label: "Activar", permission: "configuracion.gestionar", states: ["INACTIVA"], tone: "success" },
    { key: "desactivar", label: "Desactivar", permission: "configuracion.gestionar", states: ["ACTIVA"], tone: "danger", confirm: "La unidad quedará inactiva y no podrá usarse en nuevas asignaciones." },
  ]} />;
}
