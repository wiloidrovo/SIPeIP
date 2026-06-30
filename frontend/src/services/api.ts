const API_BASE_URL = "http://127.0.0.1:8000/api";

export type Rol = {
  id: number;
  nombre: string;
  descripcion: string;
  activo: boolean;
  permisos: string[];
  fecha_creacion: string;
  fecha_actualizacion: string;
};

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

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Error en la solicitud");
  }

  if (response.status === 204) {
    return null as T;
  }

  return response.json();
}

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
};

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
