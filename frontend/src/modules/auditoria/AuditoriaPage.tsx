import { useCallback, useEffect, useMemo, useState } from "react";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { EmptyState, Feedback, LoadingState } from "../../components/States";
import { apiRequest, normalizeList } from "../../services/api";

type AuditValue = string | number | boolean | null | AuditValue[] | { [key: string]: AuditValue };
type AuditEvent = {
  id: number;
  fecha_hora: string;
  usuario_identificador: string;
  usuario_nombre: string;
  entidad_nombre: string;
  modulo: string;
  funcionalidad: string;
  accion: string;
  tipo_entidad: string;
  registro_id: string;
  direccion_ip: string | null;
  resultado: string;
  detalle: string;
  valores_anteriores: Record<string, AuditValue>;
  valores_posteriores: Record<string, AuditValue>;
};

const FIELD_LABELS: Record<string, string> = {
  id: "Identificador",
  estado: "Estado",
  activo: "Activo",
  nombre: "Nombre",
  descripcion: "Descripción",
  entidad: "Entidad",
  entidad_id: "Entidad",
  rol: "Rol",
  rol_id: "Rol",
  responsable: "Responsable",
  responsable_id: "Responsable",
  permisos: "Permisos",
  fecha_actualizacion: "Fecha de actualización",
  fecha_creacion: "Fecha de creación",
};

function fieldLabel(field: string) {
  if (FIELD_LABELS[field]) return FIELD_LABELS[field];
  const text = field.replace(/_id$/, "").replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function valueText(value: AuditValue | undefined): string {
  if (value === undefined || value === null || value === "") return "Sin dato";
  if (value === true) return "Sí";
  if (value === false) return "No";
  if (Array.isArray(value)) return value.length ? value.map(valueText).join(", ") : "Sin datos";
  if (typeof value === "object") {
    return Object.entries(value)
      .map(([key, item]) => `${fieldLabel(key)}: ${valueText(item)}`)
      .join("; ");
  }
  const text = String(value);
  return /^[A-Z][A-Z_]+$/.test(text) ? text.replaceAll("_", " ") : text;
}

function changedFields(event: AuditEvent) {
  const previous = event.valores_anteriores ?? {};
  const next = event.valores_posteriores ?? {};
  const automaticFields = new Set(["fecha_creacion", "fecha_actualizacion", "last_login"]);
  return Array.from(new Set([...Object.keys(previous), ...Object.keys(next)]))
    .filter((key) => !automaticFields.has(key) && JSON.stringify(previous[key]) !== JSON.stringify(next[key]))
    .map((key) => ({ key, previous: previous[key], next: next[key] }));
}

export function AuditoriaPage() {
  const [records, setRecords] = useState<AuditEvent[]>([]);
  const [selected, setSelected] = useState<AuditEvent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({ modulo: "", accion: "", resultado: "", fecha_desde: "", fecha_hasta: "" });

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    if (search.trim()) params.set("search", search.trim());
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    try {
      const payload = await apiRequest<AuditEvent[] | { results: AuditEvent[] }>(
        `/auditoria/eventos/${params.size ? `?${params.toString()}` : ""}`,
      );
      setRecords(normalizeList(payload));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo consultar la auditoría.");
    } finally {
      setLoading(false);
    }
  }, [filters, search]);

  useEffect(() => { void load(); }, [load]);
  const changes = useMemo(() => selected ? changedFields(selected) : [], [selected]);

  return (
    <>
      <PageHeader
        eyebrow="Control interno"
        title="Auditoría y trazabilidad"
        description="Consulte accesos, cambios y decisiones registrados en el sistema."
      />
      <Feedback message={error} tone="error" onClose={() => setError("")} />
      <section className="panel">
        <form className="resource-filters audit-filters" onSubmit={(event) => { event.preventDefault(); void load(); }}>
          <label><span>Buscar</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Usuario, módulo o registro" /></label>
          <label><span>Módulo</span><input value={filters.modulo} onChange={(event) => setFilters((current) => ({ ...current, modulo: event.target.value }))} /></label>
          <label><span>Acción</span><input value={filters.accion} onChange={(event) => setFilters((current) => ({ ...current, accion: event.target.value.toUpperCase() }))} /></label>
          <label><span>Resultado</span><select value={filters.resultado} onChange={(event) => setFilters((current) => ({ ...current, resultado: event.target.value }))}><option value="">Todos</option><option value="EXITO">Éxito</option><option value="FALLO">Fallo</option></select></label>
          <label><span>Desde</span><input type="date" value={filters.fecha_desde} onChange={(event) => setFilters((current) => ({ ...current, fecha_desde: event.target.value }))} /></label>
          <label><span>Hasta</span><input type="date" min={filters.fecha_desde || undefined} value={filters.fecha_hasta} onChange={(event) => setFilters((current) => ({ ...current, fecha_hasta: event.target.value }))} /></label>
          <div className="resource-filters__actions">
            <button className="button button--secondary" type="submit">Aplicar filtros</button>
            <button className="button button--quiet" type="button" onClick={() => { setSearch(""); setFilters({ modulo: "", accion: "", resultado: "", fecha_desde: "", fecha_hasta: "" }); }}>Limpiar</button>
          </div>
        </form>
        {loading ? <LoadingState label="Cargando eventos" /> : records.length === 0 ? <EmptyState title="No hay eventos" detail="No se encontraron registros con los filtros seleccionados." /> : (
          <div className="table-scroll">
            <table>
              <thead><tr><th>Fecha y hora</th><th>Usuario</th><th>Módulo</th><th>Acción</th><th>Registro</th><th>Resultado</th><th>Detalle</th></tr></thead>
              <tbody>{records.map((record) => <tr key={record.id}>
                <td>{new Date(record.fecha_hora).toLocaleString("es-EC")}</td>
                <td>{record.usuario_nombre || record.usuario_identificador || "Sistema"}</td>
                <td><strong>{record.modulo}</strong><br /><span className="muted">{record.funcionalidad}</span></td>
                <td>{valueText(record.accion)}</td>
                <td>{record.tipo_entidad || "—"}{record.registro_id ? ` #${record.registro_id}` : ""}</td>
                <td><span className={`status-badge ${record.resultado === "EXITO" ? "status-badge--success" : "status-badge--danger"}`}>{record.resultado === "EXITO" ? "Éxito" : "Fallo"}</span></td>
                <td><button type="button" className="link-button" onClick={() => setSelected(record)}>Ver detalle</button></td>
              </tr>)}</tbody>
            </table>
          </div>
        )}
      </section>
      <Modal open={Boolean(selected)} onClose={() => setSelected(null)} title="Detalle del evento" wide>
        {selected ? <div className="audit-detail">
          <dl className="audit-summary">
            <div><dt>Fecha y hora</dt><dd>{new Date(selected.fecha_hora).toLocaleString("es-EC")}</dd></div>
            <div><dt>Usuario</dt><dd>{selected.usuario_nombre || selected.usuario_identificador || "Sistema"}</dd></div>
            <div><dt>Entidad</dt><dd>{selected.entidad_nombre || "Sin entidad asociada"}</dd></div>
            <div><dt>Acción</dt><dd>{valueText(selected.accion)}</dd></div>
            <div><dt>Registro</dt><dd>{selected.tipo_entidad || "Sin registro"}{selected.registro_id ? ` #${selected.registro_id}` : ""}</dd></div>
            <div><dt>Dirección IP</dt><dd>{selected.direccion_ip || "No disponible"}</dd></div>
          </dl>
          {selected.detalle ? <p className="audit-note">{selected.detalle}</p> : null}
          <h3>Cambios registrados</h3>
          {changes.length ? <div className="table-scroll"><table><thead><tr><th>Campo</th><th>Valor anterior</th><th>Valor posterior</th></tr></thead><tbody>{changes.map((change) => <tr key={change.key}><td>{fieldLabel(change.key)}</td><td>{valueText(change.previous)}</td><td>{valueText(change.next)}</td></tr>)}</tbody></table></div> : <EmptyState title="Sin cambios de campos" detail="El evento registra una consulta, acceso o acción sin modificación de datos." />}
        </div> : null}
      </Modal>
    </>
  );
}
