import { useState } from "react";
import type { ReactNode } from "react";
import { useAuth } from "../../auth/AuthContext";
import { ResourcePage, optionsFrom } from "../../components/ResourcePage";
import { apiRequest, normalizeList } from "../../services/api";
import type { ApiRecord } from "../../services/api";

const projects = optionsFrom("/proyectos/", (item) => `${String(item.codigo)} · ${String(item.nombre)}`);
const tipologies = optionsFrom("/tipologias-intervencion/", (item) => `${String(item.codigo)} · ${String(item.nombre)}`);

async function projectMilestones(record?: ApiRecord) {
  const payload = await apiRequest<ApiRecord[] | { results: ApiRecord[] }>("/hitos-proyectos/", { notify: false });
  return normalizeList(payload)
    .filter((item) => Number(item.proyecto) === record?.id && item.activo !== false)
    .map((item) => ({ value: item.id, label: `${String(item.orden)} · ${String(item.nombre)}` }));
}

function projectState(record: ApiRecord) {
  const detail = record.proyecto_detalle;
  return detail && typeof detail === "object" ? String((detail as Record<string, unknown>).estado ?? "") : "";
}

function SecondarySection({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return <details className="project-section" open={open} onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary><span><strong>{title}</strong><small>{description}</small></span></summary>
    {open ? <div className="project-section__content">{children}</div> : null}
  </details>;
}

export function ProyectosPage() {
  const { hasPermission } = useAuth();
  return <div className="stacked-pages projects-page">
    <ResourcePage
      eyebrow="Inversión pública"
      title="Proyectos de inversión"
      description="Gestione proyectos, responsables, presupuesto y avance institucional."
      apiPath="/proyectos/"
      viewPermission="proyectos.ver"
      createPermission="proyectos.crear"
      editPermission="proyectos.editar"
      deletePermission="proyectos.eliminar"
      fields={[
        { name: "entidad", label: "Entidad", type: "select", required: true, readOnlyOnEdit: true, loadOptions: optionsFrom("/configuracion/entidades/", (item) => `${String(item.codigo_oficial)} · ${String(item.nombre)}`) },
        { name: "plan", label: "Plan", type: "select", required: true, loadOptions: optionsFrom("/planes/", (item) => String(item.nombre)) },
        { name: "objetivo_estrategico", label: "Objetivo estratégico", type: "select", required: true, loadOptions: optionsFrom("/objetivos-estrategicos/", (item) => `${String(item.codigo)} · ${String(item.nombre)}`) },
        { name: "codigo", label: "Código", required: true },
        { name: "nombre", label: "Nombre", required: true },
        { name: "descripcion", label: "Descripción", type: "textarea" },
        { name: "tipologia_intervencion", label: "Tipología de intervención", type: "select", required: true, loadOptions: tipologies },
        ...(hasPermission("usuarios.ver") ? [{ name: "responsable", label: "Responsable", type: "select" as const, emptyAsNull: true, loadOptions: optionsFrom("/usuarios/", (item) => `${String(item.first_name)} ${String(item.last_name)}`.trim() || String(item.username)) }] : []),
        { name: "fecha_inicio", label: "Fecha de inicio", type: "date", required: true },
        { name: "fecha_fin", label: "Fecha de fin", type: "date", required: true },
        { name: "presupuesto_estimado", label: "Presupuesto estimado", type: "number", min: 0, step: "0.01", required: true },
      ]}
      columns={[
        { key: "codigo", label: "Código" },
        { key: "nombre", label: "Proyecto" },
        { key: "entidad_detalle.nombre", label: "Entidad" },
        { key: "responsable_detalle.nombre_completo", label: "Responsable" },
        { key: "presupuesto_estimado", label: "Presupuesto", render: (item) => Number(item.presupuesto_estimado).toLocaleString("es-EC", { style: "currency", currency: "USD" }) },
        { key: "avance_fisico", label: "Avance físico", render: (item) => `${String(item.avance_fisico)}%` },
        { key: "estado", label: "Estado" },
      ]}
      actions={[
        { key: "planificar", label: "Planificar", permission: "proyectos.editar", states: ["BORRADOR"], tone: "success" },
        { key: "enviar-a-revision", label: "Enviar a revisión", permission: "proyectos.enviar_revision", states: ["PLANIFICADO"], confirm: "El proyecto quedará pendiente de decisión." },
        { key: "devolver", label: "Devolver", permission: "proyectos.devolver", states: ["EN_REVISION"], tone: "danger", formFields: [{ name: "observacion", label: "Observación para correcciones", type: "textarea", required: true }] },
        { key: "aprobar", label: "Aprobar", permission: "proyectos.aprobar", states: ["EN_REVISION"], tone: "success", confirm: "Confirme la aprobación del proyecto." },
        { key: "iniciar-ejecucion", label: "Iniciar ejecución", permission: "proyectos.editar", states: ["APROBADO"], tone: "success" },
        { key: "suspender", label: "Suspender", permission: "proyectos.editar", states: ["EN_EJECUCION"], tone: "danger", confirm: "El proyecto quedará suspendido." },
        { key: "reanudar", label: "Reanudar", permission: "proyectos.editar", states: ["SUSPENDIDO"], tone: "success" },
        { key: "finalizar", label: "Finalizar", permission: "proyectos.editar", states: ["EN_EJECUCION"], confirm: "Confirme el cierre de la ejecución." },
        { key: "archivar", label: "Archivar", permission: "proyectos.archivar", states: ["BORRADOR", "PLANIFICADO", "APROBADO", "SUSPENDIDO", "FINALIZADO"], tone: "danger", confirm: "El proyecto quedará archivado y conservará su historial." },
        { key: "registrar-seguimiento", label: "Registrar seguimiento", permission: "proyectos.registrar_seguimiento", states: ["EN_EJECUCION", "SUSPENDIDO"], formFields: [
          { name: "hito", label: "Hito relacionado", type: "select", emptyAsNull: true, loadOptions: projectMilestones },
          { name: "fecha_registro", label: "Fecha", type: "date", required: true },
          { name: "avance_fisico", label: "Avance físico (%)", type: "number", min: 0, max: 100, step: "0.01", required: true },
          { name: "avance_financiero", label: "Avance financiero (%)", type: "number", min: 0, max: 100, step: "0.01", required: true },
          { name: "observacion", label: "Observación", type: "textarea" },
        ] },
      ]}
      canEdit={(item) => ["BORRADOR", "PLANIFICADO"].includes(String(item.estado))}
      canDelete={(item) => String(item.estado) === "BORRADOR" && Number(item.hitos_count) === 0 && Number(item.seguimientos_count) === 0}
    />

    <section className="project-secondary" aria-label="Información complementaria de proyectos">
      <SecondarySection title="Cronograma e hitos" description="Defina etapas y fechas planificadas.">
        <ResourcePage eyebrow="Cronograma" title="Hitos de proyectos" description="Organice las etapas que componen cada proyecto." apiPath="/hitos-proyectos/" viewPermission="proyectos.ver" createPermission="proyectos.editar" editPermission="proyectos.editar" deletePermission="proyectos.editar" fields={[
          { name: "proyecto", label: "Proyecto", type: "select", required: true, readOnlyOnEdit: true, loadOptions: projects },
          { name: "orden", label: "Orden", type: "number", min: 1, required: true },
          { name: "nombre", label: "Nombre", required: true },
          { name: "descripcion", label: "Descripción", type: "textarea" },
          { name: "fecha_inicio_planificada", label: "Inicio planificado", type: "date", required: true },
          { name: "fecha_fin_planificada", label: "Fin planificado", type: "date", required: true },
          { name: "porcentaje_planificado", label: "Peso planificado (%)", type: "number", min: 0, max: 100, step: "0.01", required: true },
          { name: "activo", label: "Hito activo", type: "checkbox" },
        ]} initialValues={{ activo: true }} columns={[
          { key: "proyecto_detalle.nombre", label: "Proyecto" }, { key: "orden", label: "Orden" }, { key: "nombre", label: "Hito" }, { key: "fecha_fin_planificada", label: "Fecha límite" }, { key: "porcentaje_planificado", label: "Peso" }, { key: "activo", label: "Activo" },
        ]} canEdit={(record) => ["BORRADOR", "PLANIFICADO"].includes(projectState(record))} canDelete={(record) => ["BORRADOR", "PLANIFICADO"].includes(projectState(record))} />
      </SecondarySection>

      <SecondarySection title="Historial de seguimiento" description="Consulte los avances físicos y financieros registrados.">
        <ResourcePage eyebrow="Seguimiento" title="Historial de avances" description="Cortes de avance registrados para cada proyecto." apiPath="/seguimientos-proyectos/" viewPermission="proyectos.ver" columns={[
          { key: "fecha_registro", label: "Fecha" }, { key: "proyecto_detalle.nombre", label: "Proyecto" }, { key: "hito_detalle.nombre", label: "Hito" }, { key: "avance_fisico", label: "Físico (%)" }, { key: "avance_financiero", label: "Financiero (%)" }, { key: "observacion", label: "Observación" }, { key: "registrado_por_detalle.nombre_completo", label: "Registrado por" },
        ]} />
      </SecondarySection>

      <SecondarySection title="Tipologías de intervención" description="Administre el catálogo utilizado por los proyectos.">
        <ResourcePage eyebrow="Configuración" title="Tipologías de intervención" description="Catálogo de clasificaciones disponibles para los proyectos." apiPath="/tipologias-intervencion/" viewPermission="proyectos.ver" createPermission="proyectos.gestionar_catalogos" editPermission="proyectos.gestionar_catalogos" deletePermission="proyectos.gestionar_catalogos" fields={[
          { name: "codigo", label: "Código", required: true }, { name: "nombre", label: "Nombre", required: true }, { name: "descripcion", label: "Descripción", type: "textarea" },
        ]} columns={[
          { key: "codigo", label: "Código" }, { key: "nombre", label: "Tipología" }, { key: "descripcion", label: "Descripción" }, { key: "activo", label: "Activa" },
        ]} actions={[
          { key: "activar", label: "Activar", permission: "proyectos.gestionar_catalogos", stateField: "activo", states: ["false"], tone: "success" },
          { key: "desactivar", label: "Desactivar", permission: "proyectos.gestionar_catalogos", stateField: "activo", states: ["true"], tone: "danger", confirm: "La tipología dejará de estar disponible para nuevos proyectos." },
        ]} />
      </SecondarySection>
    </section>
  </div>;
}
