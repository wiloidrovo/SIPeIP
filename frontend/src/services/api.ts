const API_BASE_URL = "http://127.0.0.1:8000/api";

/**
 * Representa un rol en el sistema, encargado de agrupar permisos.
 */
export type Rol = {
  id: number;
  nombre: string;
  descripcion: string;
  activo: boolean;
  permisos: string[];
  usuarios_count: number;
  fecha_creacion: string;
  fecha_actualizacion: string;
};

/**
 * Representa un usuario del sistema y sus credenciales de acceso.
 */
export type Usuario = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  rol: number | null;
  rol_detalle: Rol | null;
  estado: "ACTIVO" | "INACTIVO" | "BLOQUEADO";
  telefono: string;
  is_active: boolean;
  is_staff: boolean;
  date_joined: string;
};

export type Plan = {
  id: number;
  nombre: string;
  descripcion: string;
  periodo_inicio: string;
  periodo_fin: string;
  responsable: number | null;
  responsable_detalle: {
    id: number;
    username: string;
    nombre_completo: string;
    email: string;
  } | null;
  estado: "BORRADOR" | "EN_REVISION" | "APROBADO" | "RECHAZADO" | "ARCHIVADO";
  activo: boolean;
  fecha_creacion: string;
  fecha_actualizacion: string;
};

export type MetaInstitucional = {
  id: number;
  plan: number;
  plan_detalle: {
    id: number;
    nombre: string;
    estado: Plan["estado"];
  };
  nombre: string;
  descripcion: string;
  resultado_esperado: string;
  fecha_inicio: string;
  fecha_fin: string;
  estado: "BORRADOR" | "ACTIVA" | "CERRADA" | "ARCHIVADA";
  activa: boolean;
  indicadores_count: number;
  fecha_creacion: string;
  fecha_actualizacion: string;
};

export type Indicador = {
  id: number;
  meta: number;
  meta_detalle: {
    id: number;
    nombre: string;
    plan: string;
  };
  nombre: string;
  descripcion: string;
  unidad_medida: string;
  valor_base: string;
  valor_meta: string;
  valor_actual: string;
  frecuencia: "MENSUAL" | "TRIMESTRAL" | "SEMESTRAL" | "ANUAL";
  activo: boolean;
  avances_count: number;
  fecha_creacion: string;
  fecha_actualizacion: string;
};

export type AvanceIndicador = {
  id: number;
  indicador: number;
  indicador_detalle: {
    id: number;
    nombre: string;
    meta: string;
    unidad_medida: string;
  };
  fecha_registro: string;
  valor: string;
  observacion: string;
  registrado_por: number | null;
  registrado_por_detalle: {
    id: number;
    username: string;
    nombre_completo: string;
  } | null;
  fecha_creacion: string;
};

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${url}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    ...options,
  });

  if (response.status === 204) {
    return null as T;
  }

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    if (typeof data === "string" && data.trim().startsWith("<!DOCTYPE html")) {
      throw new Error(
        "Ocurrió un error interno en el servidor. Revise la consola del backend.",
      );
    }

    throw new Error(formatApiError(data));
  }

  return data;
}

function formatApiError(error: unknown): string {
  if (typeof error === "string") {
    return error || "Error en la solicitud.";
  }

  if (Array.isArray(error)) {
    return error.map(String).join(" ");
  }

  if (error && typeof error === "object") {
    const messages = Object.entries(error).flatMap(([field, value]) => {
      if (Array.isArray(value)) {
        return value.map((item) => `${field}: ${item}`);
      }

      if (typeof value === "string") {
        return `${field}: ${value}`;
      }

      if (value && typeof value === "object") {
        return `${field}: ${formatApiError(value)}`;
      }

      return `${field}: ${String(value)}`;
    });

    return messages.join(" | ") || "Error en la solicitud.";
  }

  return "Error en la solicitud.";
}

/**
 * Servicio de comunicación con la API para la gestión de Roles.
 */
export const rolesApi = {
  listar: () => request<Rol[]>("/roles/"),

  crear: (data: Pick<Rol, "nombre" | "descripcion" | "activo">) =>
    request<Rol>("/roles/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  eliminar: (id: number) =>
    request<null>(`/roles/${id}/`, {
      method: "DELETE",
    }),

  asignarPermisos: (id: number, permisos: string[]) =>
    request<Rol>(`/roles/${id}/asignar-permisos/`, {
      method: "POST",
      body: JSON.stringify({ permisos }),
    }),

  activar: (id: number) =>
    request<Rol>(`/roles/${id}/activar/`, {
      method: "POST",
    }),

  desactivar: (id: number) =>
    request<Rol>(`/roles/${id}/desactivar/`, {
      method: "POST",
    }),

  actualizar: (
    id: number,
    data: Partial<Pick<Rol, "nombre" | "descripcion" | "activo" | "permisos">>,
  ) =>
    request<Rol>(`/roles/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
};

/**
 * Servicio de comunicación con la API para la gestión de Usuarios.
 */
export const usuariosApi = {
  listar: () => request<Usuario[]>("/usuarios/"),

  crear: (data: {
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    password: string;
    rol: number | null;
    estado: "ACTIVO" | "INACTIVO" | "BLOQUEADO";
    telefono: string;
    is_active: boolean;
    is_staff: boolean;
  }) =>
    request<Usuario>("/usuarios/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  actualizar: (
    id: number,
    data: Partial<{
      username: string;
      email: string;
      first_name: string;
      last_name: string;
      password: string;
      rol: number | null;
      estado: "ACTIVO" | "INACTIVO" | "BLOQUEADO";
      telefono: string;
      is_active: boolean;
      is_staff: boolean;
    }>,
  ) =>
    request<Usuario>(`/usuarios/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  eliminar: (id: number) =>
    request<null>(`/usuarios/${id}/`, {
      method: "DELETE",
    }),

  activar: (id: number) =>
    request<Usuario>(`/usuarios/${id}/activar/`, {
      method: "POST",
    }),

  bloquear: (id: number) =>
    request<Usuario>(`/usuarios/${id}/bloquear/`, {
      method: "POST",
    }),
};

export const planesApi = {
  listar: () => request<Plan[]>("/planes/"),

  crear: (
    data: Pick<
      Plan,
      | "nombre"
      | "descripcion"
      | "periodo_inicio"
      | "periodo_fin"
      | "responsable"
      | "estado"
      | "activo"
    >,
  ) =>
    request<Plan>("/planes/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  actualizar: (
    id: number,
    data: Partial<
      Pick<
        Plan,
        | "nombre"
        | "descripcion"
        | "periodo_inicio"
        | "periodo_fin"
        | "responsable"
        | "estado"
        | "activo"
      >
    >,
  ) =>
    request<Plan>(`/planes/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  eliminar: (id: number) =>
    request<null>(`/planes/${id}/`, {
      method: "DELETE",
    }),

  enviarARevision: (id: number) =>
    request<Plan>(`/planes/${id}/enviar-a-revision/`, {
      method: "POST",
    }),

  archivar: (id: number) =>
    request<Plan>(`/planes/${id}/archivar/`, {
      method: "POST",
    }),
};

export const metasApi = {
  listar: () => request<MetaInstitucional[]>("/metas/"),

  crear: (
    data: Pick<
      MetaInstitucional,
      | "plan"
      | "nombre"
      | "descripcion"
      | "resultado_esperado"
      | "fecha_inicio"
      | "fecha_fin"
      | "estado"
      | "activa"
    >,
  ) =>
    request<MetaInstitucional>("/metas/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  actualizar: (
    id: number,
    data: Partial<
      Pick<
        MetaInstitucional,
        | "plan"
        | "nombre"
        | "descripcion"
        | "resultado_esperado"
        | "fecha_inicio"
        | "fecha_fin"
        | "estado"
        | "activa"
      >
    >,
  ) =>
    request<MetaInstitucional>(`/metas/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  eliminar: (id: number) =>
    request<null>(`/metas/${id}/`, {
      method: "DELETE",
    }),

  archivar: (id: number) =>
    request<MetaInstitucional>(`/metas/${id}/archivar/`, {
      method: "POST",
    }),
};

export const indicadoresApi = {
  listar: () => request<Indicador[]>("/indicadores/"),

  crear: (
    data: Pick<
      Indicador,
      | "meta"
      | "nombre"
      | "descripcion"
      | "unidad_medida"
      | "valor_base"
      | "valor_meta"
      | "frecuencia"
      | "activo"
    >,
  ) =>
    request<Indicador>("/indicadores/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  actualizar: (
    id: number,
    data: Partial<
      Pick<
        Indicador,
        | "meta"
        | "nombre"
        | "descripcion"
        | "unidad_medida"
        | "valor_base"
        | "valor_meta"
        | "frecuencia"
        | "activo"
      >
    >,
  ) =>
    request<Indicador>(`/indicadores/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  eliminar: (id: number) =>
    request<null>(`/indicadores/${id}/`, {
      method: "DELETE",
    }),

  registrarAvance: (
    id: number,
    data: {
      fecha_registro: string;
      valor: string;
      observacion: string;
      registrado_por: number | null;
    },
  ) =>
    request<AvanceIndicador>(`/indicadores/${id}/registrar-avance/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  activar: (id: number) =>
    request<Indicador>(`/indicadores/${id}/activar/`, {
      method: "POST",
    }),

  desactivar: (id: number) =>
    request<Indicador>(`/indicadores/${id}/desactivar/`, {
      method: "POST",
    }),
};

export const avancesIndicadoresApi = {
  listar: () => request<AvanceIndicador[]>("/avances-indicadores/"),
};
