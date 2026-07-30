import { Link } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { ResourcePage, optionsFrom } from "../../components/ResourcePage";
import type {
  SelectFilterContext,
  SelectOption,
} from "../../components/ResourcePage";
import { OdsBadges, TrackingStatus } from "../../components/TrackingStatus";

const entities = optionsFrom(
  "/configuracion/entidades/",
  (item) => `${String(item.codigo_oficial)} · ${String(item.nombre)}`,
  (item) => String(item.estado) !== "ACTIVA",
);

function optionEntityId(option: SelectOption) {
  const entity = option.record?.entidad;
  if (typeof entity === "number" || typeof entity === "string") {
    return String(entity);
  }
  const detail = option.record?.entidad_detalle;
  if (detail && typeof detail === "object") {
    return String((detail as Record<string, unknown>).id ?? "");
  }
  return "";
}

function matchesSelectedEntity(
  option: SelectOption,
  context: SelectFilterContext,
) {
  const entityId = String(context.values.entidad ?? "");
  return Boolean(entityId && optionEntityId(option) === entityId);
}

function alignmentValue(item: Record<string, unknown>) {
  return item.alineaciones ?? item.ods_resumen ?? item.ods ?? [];
}

export function PlanesPage() {
  const { hasPermission, user } = useAuth();
  const scope = user?.rol?.alcance;
  const hasInstitutionalScope = Boolean(
    user?.institucion && !["GLOBAL", "TOTAL"].includes(scope ?? ""),
  );
  return <ResourcePage eyebrow="Planificación" title="Planes institucionales" description="Cree planes, abra su expediente y gestione cada etapa mediante acciones autorizadas." apiPath="/planes/" viewPermission="planes.ver" createPermission="planes.crear" editPermission="planes.editar" deletePermission="planes.eliminar" initialValues={{ responsable: "", entidad: "" }} fields={[
    {
      name: "entidad",
      label: "Entidad",
      type: "select",
      emptyAsNull: true,
      loadOptions: entities,
      readOnlyOnEdit: true,
      emptyOptionsMessage: "No hay entidades activas dentro de su ámbito.",
    },
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
        (item) => item.is_active !== true || String(item.estado) !== "ACTIVO",
      ),
      filterOptions: matchesSelectedEntity,
      dependsOn: ["entidad"],
      emptyOptionsMessage: (context: SelectFilterContext) => context.values.entidad
        ? "No hay usuarios activos en la entidad seleccionada."
        : "Seleccione primero una entidad.",
    }] : []),
  ]} columns={[
    {
      key: "nombre",
      label: "Plan",
      render: (item) => (
        <span>
          <Link className="table-primary-link" to={`/planes/${item.id}`}>
            {String(item.nombre)}
          </Link>
          <small className="table-detail">Abrir expediente completo</small>
        </span>
      ),
    },
    { key: "entidad_detalle.nombre", label: "Entidad" },
    { key: "responsable_detalle.nombre_completo", label: "Responsable" },
    { key: "estado", label: "Estado" },
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
      key: "ods_resumen",
      label: "ODS",
      render: (item) => {
        const alignments = alignmentValue(item);
        if (Array.isArray(alignments) && alignments.length) {
          return <OdsBadges value={alignments} />;
        }
        const count = Number(item.ods_count ?? 0);
        return count > 0 ? (
          <span className="data-tag">{count} ODS vinculado{count === 1 ? "" : "s"}</span>
        ) : <span className="muted">Sin ODS asociado</span>;
      },
    },
  ]} actions={[
    { key: "archivar", label: "Archivar", permission: "planes.archivar", states: ["BORRADOR", "DEVUELTO", "RECHAZADO"], tone: "danger", confirm: "El plan quedará inactivo y archivado, conservando su trazabilidad." },
    { key: "archivar-aprobado", endpoint: "archivar", label: "Archivar", permission: "planes.archivar", allPermissions: ["planes.aprobar"], states: ["APROBADO"], tone: "danger", confirm: "El plan aprobado quedará inactivo y archivado, conservando toda su trazabilidad." },
  ]} extraContent={hasInstitutionalScope ? (
    <section className="panel dashboard-guidance" aria-label="Ámbito de los planes">
      <div>
        <span className="eyebrow">Ámbito de consulta</span>
        <h2>{user?.institucion?.codigo_oficial} · {user?.institucion?.nombre}</h2>
        <p>
          {scope === "REVISION_ENTIDAD"
            ? "Además de los registros de su institución, esta bandeja muestra planes de otras entidades cuando han sido enviados a revisión."
            : "Esta cuenta solo gestiona los planes propios o asignados dentro de la institución indicada."}
        </p>
      </div>
    </section>
  ) : null} canEdit={(item) => ["BORRADOR", "DEVUELTO", "RECHAZADO"].includes(String(item.estado))} canDelete={(item) => ["BORRADOR", "DEVUELTO", "RECHAZADO", "ARCHIVADO"].includes(String(item.estado))} />;
}
