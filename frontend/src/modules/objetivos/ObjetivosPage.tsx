import { ResourcePage, optionsFrom } from "../../components/ResourcePage";

export function ObjetivosPage() {
  return <ResourcePage eyebrow="Estrategia institucional" title="Objetivos estratégicos" description="Administre los objetivos estratégicos de cada entidad." apiPath="/objetivos-estrategicos/" viewPermission="objetivos.ver" createPermission="objetivos.gestionar" editPermission="objetivos.gestionar" deletePermission="objetivos.gestionar" fields={[
    { name: "entidad", label: "Entidad", type: "select", required: true, loadOptions: optionsFrom("/configuracion/entidades/", (item) => `${String(item.codigo_oficial)} · ${String(item.nombre)}`, (item) => String(item.estado) !== "ACTIVA") },
    { name: "codigo", label: "Código", required: true }, { name: "nombre", label: "Nombre", required: true }, { name: "descripcion", label: "Descripción", type: "textarea" },
  ]} columns={[
    { key: "codigo", label: "Código" }, { key: "nombre", label: "Objetivo" }, { key: "entidad_detalle.nombre", label: "Entidad" }, { key: "estado", label: "Estado" }, { key: "fecha_actualizacion", label: "Actualización", render: (item) => new Date(String(item.fecha_actualizacion)).toLocaleDateString("es-EC") },
  ]} actions={[
    { key: "activar", label: "Activar", permission: "objetivos.gestionar", states: ["INACTIVO"], tone: "success" },
    { key: "desactivar", label: "Desactivar", permission: "objetivos.gestionar", states: ["ACTIVO"], tone: "danger", confirm: "El objetivo dejará de estar disponible para nuevas alineaciones." },
  ]} />;
}
