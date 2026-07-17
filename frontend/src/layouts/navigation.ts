export type NavigationItem = {
  label: string;
  path: string;
  permission?: string;
  mark: string;
};

export type NavigationGroup = { label: string; items: NavigationItem[] };

export const navigation: NavigationGroup[] = [
  {
    label: "Inicio",
    items: [{ label: "Panel institucional", path: "/dashboard", mark: "D" }],
  },
  {
    label: "Administración",
    items: [
      { label: "Usuarios", path: "/usuarios", permission: "usuarios.ver", mark: "U" },
      { label: "Roles y permisos", path: "/roles", permission: "roles.ver", mark: "R" },
      { label: "Entidades", path: "/configuracion/entidades", permission: "configuracion.ver", mark: "E" },
      { label: "Unidades", path: "/configuracion/unidades", permission: "configuracion.ver", mark: "N" },
    ],
  },
  {
    label: "Planificación",
    items: [
      { label: "Planes", path: "/planes", permission: "planes.ver", mark: "P" },
      { label: "Metas", path: "/metas", permission: "metas.ver", mark: "M" },
      { label: "Indicadores", path: "/indicadores", permission: "indicadores.ver", mark: "I" },
      { label: "Avances", path: "/avances", permission: "indicadores.ver", mark: "A" },
      { label: "Objetivos", path: "/objetivos", permission: "objetivos.ver", mark: "O" },
    ],
  },
  {
    label: "Alineación",
    items: [
      { label: "Plan Nacional", path: "/alineacion/pnd", permission: "alineaciones.ver", mark: "P" },
      { label: "ODS", path: "/alineacion/ods", permission: "alineaciones.ver", mark: "O" },
    ],
  },
  {
    label: "Gestión",
    items: [
      { label: "Proyectos", path: "/proyectos", permission: "proyectos.ver", mark: "Y" },
      { label: "Reportes", path: "/reportes", permission: "reportes.ver", mark: "R" },
      { label: "Auditoría", path: "/auditoria", permission: "auditoria.ver", mark: "T" },
    ],
  },
];
