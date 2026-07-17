import { ResourcePage, optionsFrom } from "../../components/ResourcePage";

export function PndPage() {
  return (
    <div className="stacked-pages">
      <ResourcePage
        eyebrow="Alineación nacional"
        title="Ejes del PND"
        description="Administre los ejes utilizados para la alineación institucional."
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
        description="Administre los objetivos agrupados por cada eje."
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
        description="Relacione los objetivos institucionales con el PND y los ODS."
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
              (item) => `${String(item.codigo)} · ${String(item.nombre)}`,
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
              (item) => `${String(item.codigo)} · ${String(item.nombre)}`,
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
          { key: "objetivo_estrategico_detalle.nombre", label: "Objetivo institucional" },
          { key: "objetivo_pnd_detalle.nombre", label: "Objetivo PND" },
          { key: "ods_detalle.nombre", label: "ODS" },
          { key: "estado", label: "Estado" },
          { key: "usuario_validador_detalle.nombre_completo", label: "Validado por" },
        ]}
        actions={[
          { key: "validar", label: "Validar", permission: "alineaciones.validar", states: ["BORRADOR"], tone: "success", confirm: "Confirme que la alineación está sustentada y puede validarse." },
          { key: "rechazar", label: "Rechazar", permission: "alineaciones.validar", states: ["BORRADOR"], tone: "danger", confirm: "La alineación quedará rechazada para corrección." },
          { key: "reabrir", label: "Reabrir", permission: "alineaciones.gestionar", states: ["RECHAZADA"] },
        ]}
        canEdit={(item) => String(item.estado) === "BORRADOR"}
        canDelete={(item) => String(item.estado) === "BORRADOR"}
      />
    </div>
  );
}
