import { useAuth } from "../../auth/AuthContext";
import { ResourcePage } from "../../components/ResourcePage";

export function EntidadesPage() {
  const { user } = useAuth();
  const scope = user?.rol?.alcance;
  const hasInstitutionalScope = Boolean(
    user?.institucion && !["GLOBAL", "TOTAL"].includes(scope ?? ""),
  );

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
  ]} extraContent={hasInstitutionalScope ? (
    <section className="panel dashboard-guidance" aria-label="Ámbito institucional">
      <div>
        <span className="eyebrow">Institución asignada</span>
        <h2>{user?.institucion?.codigo_oficial} · {user?.institucion?.nombre}</h2>
        <p>Esta cuenta solo consulta su institución. Crear una entidad nueva no cambia automáticamente la institución asignada a los usuarios existentes.</p>
      </div>
    </section>
  ) : null} />;
}
