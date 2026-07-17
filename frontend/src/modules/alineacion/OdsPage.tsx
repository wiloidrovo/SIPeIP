import { ResourcePage } from "../../components/ResourcePage";

export function OdsPage() {
  return <ResourcePage eyebrow="Agenda global" title="Objetivos de Desarrollo Sostenible" description="Administre los ODS utilizados en la alineación institucional." apiPath="/ods/" viewPermission="alineaciones.ver" createPermission="alineaciones.gestionar_catalogos" editPermission="alineaciones.gestionar_catalogos" deletePermission="alineaciones.gestionar_catalogos" fields={[
    { name: "numero", label: "Número", type: "number", min: 1, required: true }, { name: "nombre", label: "Nombre", required: true }, { name: "descripcion", label: "Descripción", type: "textarea" },
  ]} columns={[{ key: "numero", label: "Número" }, { key: "nombre", label: "ODS" }, { key: "descripcion", label: "Descripción" }, { key: "estado", label: "Estado" }]} actions={[
    { key: "activar", label: "Activar", permission: "alineaciones.gestionar_catalogos", states: ["INACTIVO"], tone: "success" }, { key: "desactivar", label: "Desactivar", permission: "alineaciones.gestionar_catalogos", states: ["ACTIVO"], tone: "danger", confirm: "El ODS no estará disponible para nuevas alineaciones." },
  ]} />;
}
