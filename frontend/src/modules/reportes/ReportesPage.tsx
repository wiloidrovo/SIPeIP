import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import { apiErrorMessage } from "../../components/ResourcePage";
import { EmptyState, Feedback, LoadingState } from "../../components/States";
import { apiDownload, apiRequest, normalizeList } from "../../services/api";

type Report = {
  codigo: string;
  nombre: string;
  descripcion: string;
  filtros: string[];
  formatos: string[];
  puede_generar: boolean;
  puede_exportar: boolean;
};
type Preview = { nombre: string; total: number; columnas: { campo: string; titulo: string }[]; resultados: Record<string, unknown>[] };
type Entity = { id: number; codigo_oficial: string; nombre: string };

const FORMAT_LABELS: Record<string, string> = { pdf: "PDF", xlsx: "Excel", csv: "CSV", json: "JSON" };

function displayValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (value === true) return "Sí";
  if (value === false) return "No";
  const text = String(value);
  if (/^\d{4}-\d{2}-\d{2}(T.*)?$/.test(text)) {
    const date = new Date(text.length === 10 ? `${text}T00:00:00` : text);
    if (!Number.isNaN(date.getTime())) return text.includes("T") ? date.toLocaleString("es-EC") : date.toLocaleDateString("es-EC");
  }
  return /^[A-Z][A-Z_]+$/.test(text) ? text.replaceAll("_", " ") : text;
}

export function ReportesPage() {
  const [catalog, setCatalog] = useState<Report[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [selected, setSelected] = useState<Report | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiRequest<Report[]>("/reportes/catalogo/"),
      apiRequest<Entity[] | { results: Entity[] }>("/configuracion/entidades/", { notify: false })
        .then(normalizeList)
        .catch(() => []),
    ])
      .then(([reports, availableEntities]) => { setCatalog(reports); setEntities(availableEntities); })
      .catch((cause) => setError(apiErrorMessage(cause)))
      .finally(() => setLoading(false));
  }, []);

  const activeFilters = useMemo(() => new Set(selected?.filtros ?? []), [selected]);
  const query = () => new URLSearchParams(
    Object.entries(filters).filter(([key, value]) => activeFilters.has(key) && value),
  ).toString();

  function choose(report: Report) {
    setSelected(report);
    setPreview(null);
    setFilters({});
    setError("");
  }

  async function generate(report: Report) {
    setBusy(true); setError("");
    try {
      const suffix = query();
      setPreview(await apiRequest<Preview>(`/reportes/generar/${report.codigo}/${suffix ? `?${suffix}` : ""}`));
    } catch (cause) { setError(apiErrorMessage(cause)); } finally { setBusy(false); }
  }

  async function download(report: Report, format: string) {
    setBusy(true); setError("");
    try {
      const suffix = query();
      const blob = await apiDownload(`/reportes/exportar/${report.codigo}/${format}/${suffix ? `?${suffix}` : ""}`);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `sipeip-${report.codigo}.${format}`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (cause) { setError(apiErrorMessage(cause)); } finally { setBusy(false); }
  }

  const setFilter = (name: string, value: string) => setFilters((current) => ({ ...current, [name]: value }));

  return (
    <>
      <PageHeader eyebrow="Información institucional" title="Reportes y exportaciones" description="Consulte y descargue información dentro de su ámbito institucional." />
      <Feedback message={error} tone="error" onClose={() => setError("")} />
      {loading ? <LoadingState label="Cargando reportes" /> : catalog.length ? (
        <section className="report-grid">
          {catalog.map((report) => <article className={`report-card${selected?.codigo === report.codigo ? " report-card--selected" : ""}`} key={report.codigo}>
            <div><h2>{report.nombre}</h2><p>{report.descripcion}</p></div>
            <button type="button" className="button button--secondary" onClick={() => choose(report)}>{selected?.codigo === report.codigo ? "Seleccionado" : "Seleccionar"}</button>
          </article>)}
        </section>
      ) : <EmptyState title="No hay reportes disponibles" detail="No existen reportes habilitados para esta cuenta." />}

      {selected ? <section className="panel report-workspace">
        <div className="panel-title"><div><span className="eyebrow">Reporte seleccionado</span><h2>{selected.nombre}</h2></div></div>
        {selected.filtros.length ? <div className="report-filters">
          {activeFilters.has("buscar") ? <label><span>Buscar</span><input value={filters.buscar ?? ""} onChange={(event) => setFilter("buscar", event.target.value)} /></label> : null}
          {activeFilters.has("estado") ? <label><span>Estado</span><input value={filters.estado ?? ""} onChange={(event) => setFilter("estado", event.target.value.toUpperCase())} /></label> : null}
          {activeFilters.has("activo") ? <label><span>Vigencia</span><select value={filters.activo ?? ""} onChange={(event) => setFilter("activo", event.target.value)}><option value="">Todos</option><option value="true">Activos</option><option value="false">Inactivos</option></select></label> : null}
          {activeFilters.has("entidad") && entities.length > 1 ? <label><span>Entidad</span><select value={filters.entidad ?? ""} onChange={(event) => setFilter("entidad", event.target.value)}><option value="">Todas las autorizadas</option>{entities.map((entity) => <option key={entity.id} value={entity.id}>{entity.codigo_oficial} · {entity.nombre}</option>)}</select></label> : null}
          {activeFilters.has("modulo") ? <label><span>Módulo</span><input value={filters.modulo ?? ""} onChange={(event) => setFilter("modulo", event.target.value)} /></label> : null}
          {activeFilters.has("accion") ? <label><span>Acción</span><input value={filters.accion ?? ""} onChange={(event) => setFilter("accion", event.target.value.toUpperCase())} /></label> : null}
          {activeFilters.has("resultado") ? <label><span>Resultado</span><select value={filters.resultado ?? ""} onChange={(event) => setFilter("resultado", event.target.value)}><option value="">Todos</option><option value="EXITO">Éxito</option><option value="FALLO">Fallo</option></select></label> : null}
          {activeFilters.has("fecha_desde") ? <label><span>Desde</span><input type="date" value={filters.fecha_desde ?? ""} onChange={(event) => setFilter("fecha_desde", event.target.value)} /></label> : null}
          {activeFilters.has("fecha_hasta") ? <label><span>Hasta</span><input type="date" min={filters.fecha_desde || undefined} value={filters.fecha_hasta ?? ""} onChange={(event) => setFilter("fecha_hasta", event.target.value)} /></label> : null}
        </div> : null}
        <div className="report-actions">
          {selected.puede_generar ? <button className="button button--primary" type="button" disabled={busy} onClick={() => void generate(selected)}>Vista previa</button> : null}
          {selected.puede_exportar ? selected.formatos.map((format) => <button className="button button--secondary" type="button" disabled={busy} key={format} onClick={() => void download(selected, format)}>Descargar {FORMAT_LABELS[format] ?? format.toUpperCase()}</button>) : null}
        </div>
      </section> : null}

      {preview ? <section className="panel preview-panel"><div className="panel-title"><div><span className="eyebrow">Vista previa</span><h2>{preview.nombre}</h2></div><span className="record-count">{preview.total} resultado{preview.total === 1 ? "" : "s"}</span></div>{preview.resultados.length ? <div className="table-scroll"><table><thead><tr>{preview.columnas.map((column) => <th key={column.campo}>{column.titulo}</th>)}</tr></thead><tbody>{preview.resultados.map((row, index) => <tr key={index}>{preview.columnas.map((column) => <td key={column.campo}>{displayValue(row[column.campo])}</td>)}</tr>)}</tbody></table></div> : <EmptyState />}</section> : null}
    </>
  );
}
