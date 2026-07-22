import { ResourcePage, optionsFrom } from "../../components/ResourcePage";
import type { ApiRecord } from "../../services/api";

function asRecord(value: unknown) {
  return value && typeof value === "object"
    ? (value as Record<string, unknown>)
    : null;
}

function entityContext(value: unknown) {
  const entity = asRecord(value);
  if (!entity) return "Entidad sin detalle";
  const code = String(entity.codigo_oficial ?? "").trim();
  const name = String(entity.nombre ?? "").trim();
  return [code, name].filter(Boolean).join(" · ") || "Entidad sin detalle";
}

function strategicObjectiveLabel(item: ApiRecord) {
  const code = String(item.codigo ?? "").trim();
  const name = String(item.nombre ?? "").trim();
  return `${[code, name].filter(Boolean).join(" · ")} — ${entityContext(item.entidad_detalle)}`;
}

function pndObjectiveLabel(item: ApiRecord) {
  const axis = asRecord(item.eje_detalle);
  const axisCode = String(axis?.codigo ?? "").trim();
  const objectiveCode = String(item.codigo ?? "").trim();
  const name = String(item.nombre ?? "").trim();
  const context = axisCode ? `Eje ${axisCode}` : "Eje sin detalle";
  return `${[objectiveCode, name].filter(Boolean).join(" · ")} — ${context}`;
}

export function PndPage() {
  return (
    <div className="stacked-pages">
      <ResourcePage
        eyebrow="Alineación nacional"
        title="Ejes del PND"
        description="Administre el nivel superior del catálogo PND utilizado para organizar sus objetivos nacionales."
        apiPath="/ejes-pnd/"
        viewPermission="alineaciones.ver"
        createPermission="alineaciones.gestionar_catalogos"
        editPermission="alineaciones.gestionar_catalogos"
        deletePermission="alineaciones.gestionar_catalogos"
        fields={[
          { name: "codigo", label: "Código", required: true },
          { name: "nombre", label: "Nombre", required: true },
          { name: "descripcion", label: "Descripción", type: "textarea" },
        ]}
        columns={[
          { key: "codigo", label: "Código" },
          { key: "nombre", label: "Eje" },
          { key: "estado", label: "Estado" },
        ]}
        actions={[
          { key: "activar", label: "Activar", permission: "alineaciones.gestionar_catalogos", states: ["INACTIVO"], tone: "success" },
          { key: "desactivar", label: "Desactivar", permission: "alineaciones.gestionar_catalogos", states: ["ACTIVO"], tone: "danger", confirm: "El eje no estará disponible para nuevas relaciones." },
        ]}
      />

      <ResourcePage
        eyebrow="Alineación nacional"
        title="Objetivos del PND"
        description="Administre los objetivos nacionales y el eje PND al que pertenece cada uno."
        apiPath="/objetivos-pnd/"
        viewPermission="alineaciones.ver"
        createPermission="alineaciones.gestionar_catalogos"
        editPermission="alineaciones.gestionar_catalogos"
        deletePermission="alineaciones.gestionar_catalogos"
        fields={[
          {
            name: "eje",
            label: "Eje",
            type: "select",
            required: true,
            loadOptions: optionsFrom(
              "/ejes-pnd/",
              (item) => `${String(item.codigo)} · ${String(item.nombre)}`,
              (item) => String(item.estado) !== "ACTIVO",
            ),
          },
          { name: "codigo", label: "Código", required: true },
          { name: "nombre", label: "Nombre", required: true },
          { name: "descripcion", label: "Descripción", type: "textarea" },
        ]}
        columns={[
          { key: "codigo", label: "Código" },
          { key: "nombre", label: "Objetivo" },
          { key: "eje_detalle.nombre", label: "Eje" },
          { key: "estado", label: "Estado" },
        ]}
        actions={[
          { key: "activar", label: "Activar", permission: "alineaciones.gestionar_catalogos", states: ["INACTIVO"], tone: "success" },
          { key: "desactivar", label: "Desactivar", permission: "alineaciones.gestionar_catalogos", states: ["ACTIVO"], tone: "danger" },
        ]}
      />

      <ResourcePage
        eyebrow="Matriz estratégica"
        title="Alineación PND / ODS"
        description="Defina cómo los objetivos estratégicos institucionales —y, mediante ellos, sus metas— contribuyen al PND y a los ODS."
        apiPath="/alineaciones/"
        viewPermission="alineaciones.ver"
        createPermission="alineaciones.gestionar"
        editPermission="alineaciones.gestionar"
        deletePermission="alineaciones.gestionar"
        fields={[
          {
            name: "objetivo_estrategico",
            label: "Objetivo institucional",
            type: "select",
            required: true,
            loadOptions: optionsFrom(
              "/objetivos-estrategicos/",
              strategicObjectiveLabel,
              (item) => String(item.estado) !== "ACTIVO",
            ),
          },
          {
            name: "objetivo_pnd",
            label: "Objetivo PND",
            type: "select",
            required: true,
            loadOptions: optionsFrom(
              "/objetivos-pnd/",
              pndObjectiveLabel,
              (item) => String(item.estado) !== "ACTIVO",
            ),
          },
          {
            name: "ods",
            label: "ODS",
            type: "select",
            required: true,
            loadOptions: optionsFrom(
              "/ods/",
              (item) => `ODS ${String(item.numero)} · ${String(item.nombre)}`,
              (item) => String(item.estado) !== "ACTIVO",
            ),
          },
          { name: "justificacion", label: "Justificación", type: "textarea", required: true },
        ]}
        columns={[
          {
            key: "objetivo_estrategico_detalle.nombre",
            label: "Objetivo institucional / entidad",
            render: (item) => {
              const objective = asRecord(item.objetivo_estrategico_detalle);
              const code = String(objective?.codigo ?? "").trim();
              const name = String(objective?.nombre ?? "Sin objetivo");
              return (
                <span>
                  {[code, name].filter(Boolean).join(" · ")}
                  <small className="table-detail">{entityContext(item.entidad_detalle)}</small>
                </span>
              );
            },
          },
          {
            key: "objetivo_pnd_detalle.nombre",
            label: "Objetivo PND / eje",
            render: (item) => {
              const objective = asRecord(item.objetivo_pnd_detalle);
              const axis = asRecord(objective?.eje);
              const code = String(objective?.codigo ?? "").trim();
              const name = String(objective?.nombre ?? "Sin objetivo PND");
              const axisCode = String(axis?.codigo ?? "").trim();
              const axisName = String(axis?.nombre ?? "").trim();
              return (
                <span>
                  {[code, name].filter(Boolean).join(" · ")}
                  <small className="table-detail">{[axisCode, axisName].filter(Boolean).join(" · ") || "Eje sin detalle"}</small>
                </span>
              );
            },
          },
          {
            key: "ods_detalle.nombre",
            label: "ODS",
            render: (item) => {
              const ods = asRecord(item.ods_detalle);
              return `ODS ${String(ods?.numero ?? "–")} · ${String(ods?.nombre ?? "Sin detalle")}`;
            },
          },
          { key: "justificacion", label: "Justificación" },
          { key: "estado", label: "Estado" },
          { key: "usuario_validador_detalle.nombre_completo", label: "Validado por" },
        ]}
        actions={[
          { key: "validar", label: "Validar", permission: "alineaciones.validar", states: ["BORRADOR"], tone: "success", confirm: "Confirme que la alineación está sustentada y puede validarse." },
          { key: "rechazar", label: "Rechazar", permission: "alineaciones.validar", states: ["BORRADOR"], tone: "danger", confirm: "La alineación quedará rechazada para corrección." },
          { key: "reabrir", label: "Reabrir", permission: "alineaciones.gestionar", states: ["RECHAZADA"] },
        ]}
        extraContent={(
          <section className="panel dashboard-guidance" aria-label="Relación entre metas, objetivos y alineación nacional">
            <div>
              <span className="eyebrow">Cómo se relacionan</span>
              <h2>Meta → Objetivo estratégico → PND / ODS</h2>
              <p>Cada meta se asocia con un objetivo estratégico. En esta matriz se vincula ese objetivo institucional con un objetivo del PND y un ODS, sin duplicar la meta ni su avance.</p>
            </div>
          </section>
        )}
        canEdit={(item) => String(item.estado) === "BORRADOR"}
        canDelete={(item) => String(item.estado) === "BORRADOR"}
      />
    </div>
  );
}
