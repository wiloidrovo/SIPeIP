import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { PageHeader } from "../components/PageHeader";
import { EmptyState, Feedback, LoadingState } from "../components/States";
import { apiRequest } from "../services/api";

type Widget = { codigo: string; titulo: string; valor: number; detalle: string; ruta: string };
type Dashboard = { alcance: string; entidad: { id: number; codigo_oficial: string; nombre: string } | null; widgets: Widget[] };

const SCOPE_LABELS: Record<string, string> = {
  TOTAL: "Cobertura general",
  GLOBAL: "Gestión institucional",
  ENTIDAD: "Institución asignada",
  PROPIO_ASIGNADO: "Registros propios y asignados",
  REVISION_ENTIDAD: "Revisión institucional",
  LECTURA_ENTIDAD: "Consulta institucional",
};

export function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { apiRequest<Dashboard>("/dashboard/").then(setData).catch((cause: Error) => setError(cause.message)); }, []);
  return <>
    <PageHeader eyebrow="Resumen institucional" title={`Bienvenido, ${user?.first_name || user?.username}`} description="Consulte sus principales pendientes y accesos de trabajo." />
    <Feedback message={error} tone="error" />
    {!data && !error ? <LoadingState label="Preparando el panel" /> : null}
    {data ? <>
      <section className="context-banner"><div><span>Institución</span><strong>{data.entidad?.nombre ?? "Cobertura general"}</strong></div><div><span>Acceso</span><strong>{SCOPE_LABELS[data.alcance] ?? "Institucional"}</strong></div><div><span>Perfil</span><strong>{user?.rol?.nombre ?? "Administración"}</strong></div></section>
      {data.widgets.length ? <section className="widget-grid">{data.widgets.map((widget) => <Link className="metric-card" to={widget.ruta} key={widget.codigo}><span>{widget.titulo}</span><strong>{widget.valor.toLocaleString("es-EC")}</strong><small>{widget.detalle || "Consultar registros"}</small></Link>)}</section> : <EmptyState title="Sin información pendiente" detail="No hay elementos disponibles para mostrar en este momento." />}
      <section className="panel dashboard-guidance"><div><h2>Acceso institucional</h2><p>El menú y la información disponible corresponden a sus responsabilidades asignadas.</p></div></section>
    </> : null}
  </>;
}
