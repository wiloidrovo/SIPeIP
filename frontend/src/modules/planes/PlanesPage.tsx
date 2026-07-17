import { useAuth } from "../../auth/AuthContext";
import { ResourcePage, optionsFrom } from "../../components/ResourcePage";

const entities = optionsFrom("/configuracion/entidades/", (item) => `${String(item.codigo_oficial)} · ${String(item.nombre)}`);

function renderHistory(result: unknown) {
  if (!Array.isArray(result) || result.length === 0) {
    return <p className="muted">El plan todavía no registra transiciones de estado.</p>;
  }
  return <div className="table-scroll"><table><thead><tr><th>Fecha</th><th>Acción</th><th>Transición</th><th>Responsable</th><th>Observación</th></tr></thead><tbody>{result.map((value, index) => {
    const item = value && typeof value === "object" ? value as Record<string, unknown> : {};
    const user = item.usuario_detalle && typeof item.usuario_detalle === "object" ? item.usuario_detalle as Record<string, unknown> : {};
    return <tr key={String(item.id ?? index)}><td>{new Date(String(item.fecha)).toLocaleString("es-EC")}</td><td>{String(item.accion ?? "")}</td><td>{String(item.estado_anterior ?? "").replaceAll("_", " ")} → {String(item.estado_nuevo ?? "").replaceAll("_", " ")}</td><td>{String(user.nombre_completo ?? user.username ?? "")}</td><td>{String(item.observacion || "Sin observación")}</td></tr>;
  })}</tbody></table></div>;
}

export function PlanesPage() {
  const { hasPermission } = useAuth();
  return <ResourcePage eyebrow="Planificación" title="Planes institucionales" description="Cree planes y gestione su revisión mediante acciones definidas para cada etapa." apiPath="/planes/" viewPermission="planes.ver" createPermission="planes.crear" editPermission="planes.editar" deletePermission="planes.eliminar" initialValues={{ responsable: "", entidad: "" }} fields={[
    { name: "entidad", label: "Entidad", type: "select", emptyAsNull: true, loadOptions: entities, readOnlyOnEdit: true },
    { name: "nombre", label: "Nombre del plan", required: true },
    { name: "descripcion", label: "Descripción", type: "textarea" },
    { name: "periodo_inicio", label: "Fecha de inicio", type: "date", required: true },
    { name: "periodo_fin", label: "Fecha de fin", type: "date", required: true },
    ...(hasPermission("usuarios.ver") ? [{
      name: "responsable",
      label: "Responsable",
      type: "select" as const,
      emptyAsNull: true,
      loadOptions: optionsFrom(
        "/usuarios/",
        (item) => `${String(item.first_name)} ${String(item.last_name)} (${String(item.username)})`,
      ),
    }] : []),
  ]} columns={[
    { key: "nombre", label: "Plan" }, { key: "entidad_detalle.nombre", label: "Entidad" }, { key: "responsable_detalle.nombre_completo", label: "Responsable" }, { key: "periodo_inicio", label: "Inicio" }, { key: "periodo_fin", label: "Fin" }, { key: "estado", label: "Estado" },
  ]} actions={[
    { key: "enviar-a-revision", label: "Enviar a revisión", permission: "planes.enviar_revision", states: ["BORRADOR", "DEVUELTO", "RECHAZADO"], tone: "success", confirm: "El plan saldrá de edición ordinaria y quedará disponible para revisión." },
    { key: "revisar", label: "Iniciar revisión", permission: "planes.revisar", states: ["EN_REVISION"] },
    { key: "devolver", label: "Devolver", permission: "planes.devolver", states: ["EN_REVISION_INICIADA"], tone: "danger", formFields: [{ name: "observacion", label: "Observación para correcciones", type: "textarea", required: true }] },
    { key: "aprobar", label: "Aprobar", permission: "planes.aprobar", states: ["EN_REVISION_INICIADA"], tone: "success", confirm: "Confirme la aprobación institucional del plan." },
    { key: "rechazar", label: "Rechazar", permission: "planes.rechazar", states: ["EN_REVISION_INICIADA"], tone: "danger", formFields: [{ name: "observacion", label: "Motivo del rechazo", type: "textarea", required: true }] },
    { key: "archivar", label: "Archivar", permission: "planes.archivar", states: ["BORRADOR", "DEVUELTO", "RECHAZADO"], tone: "danger", confirm: "El plan quedará inactivo y archivado, conservando su trazabilidad." },
    { key: "archivar-aprobado", endpoint: "archivar", label: "Archivar", permission: "planes.archivar", allPermissions: ["planes.aprobar"], states: ["APROBADO"], tone: "danger", confirm: "El plan aprobado quedará inactivo y archivado, conservando toda su trazabilidad." },
    { key: "historial", label: "Ver historial", permission: "planes.ver", method: "GET", resultTitle: "Historial de estados del plan", renderResult: renderHistory },
  ]} canEdit={(item) => ["BORRADOR", "DEVUELTO", "RECHAZADO"].includes(String(item.estado))} canDelete={(item) => ["BORRADOR", "DEVUELTO", "RECHAZADO", "ARCHIVADO"].includes(String(item.estado))} />;
}
