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
