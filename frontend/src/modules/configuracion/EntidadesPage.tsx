import { ResourcePage } from "../../components/ResourcePage";

export function EntidadesPage() {
  return <ResourcePage eyebrow="Configuración institucional" title="Entidades" description="Administre las entidades, su identificación y vigencia." apiPath="/configuracion/entidades/" viewPermission="configuracion.ver" createPermission="configuracion.gestionar" editPermission="configuracion.gestionar" fields={[
    { name: "codigo_oficial", label: "Código oficial", required: true },
    { name: "nombre", label: "Nombre", required: true },
    { name: "subsector", label: "Subsector", required: true },
    { name: "nivel_gobierno", label: "Nivel de gobierno", required: true },
  ]} columns={[
    { key: "codigo_oficial", label: "Código" }, { key: "nombre", label: "Entidad" }, { key: "subsector", label: "Subsector" }, { key: "nivel_gobierno", label: "Nivel" }, { key: "unidades_count", label: "Unidades" }, { key: "estado", label: "Estado" },
  ]} actions={[
    { key: "activar", label: "Activar", permission: "configuracion.gestionar", states: ["INACTIVA"], tone: "success" },
    { key: "desactivar", label: "Desactivar", permission: "configuracion.gestionar", states: ["ACTIVA"], tone: "danger", confirm: "La entidad quedará inactiva. Sus relaciones históricas se conservarán." },
  ]} />;
}
