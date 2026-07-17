export const API_ORIGIN = "http://localhost:8000";
export const API_BASE_URL = `${API_ORIGIN}/api`;

export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
export type ApiRecord = { id: number; [key: string]: unknown };

export type ApiErrorKind =
  | "network"
  | "unauthorized"
  | "forbidden"
  | "conflict"
  | "validation"
  | "internal";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly kind: ApiErrorKind,
    public readonly payload?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type RequestOptions = RequestInit & {
  retryAuth?: boolean;
  notify?: boolean;
};

let csrfToken = "";
let csrfPromise: Promise<string> | null = null;
let refreshPromise: Promise<boolean> | null = null;

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function emitSessionEvent(name: "sipeip:unauthorized" | "sipeip:forbidden") {
  window.dispatchEvent(new CustomEvent(name));
}

function asObject(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function fieldLabel(field: string) {
  if (field === "non_field_errors") return "Información";
  const text = field.replaceAll("_", " ").trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : "Información";
}

export function formatApiError(payload: unknown): string {
  if (typeof payload === "string") {
    if (payload.trim().startsWith("<")) {
      return "No se pudo procesar la respuesta recibida.";
    }
    return payload.trim() || "No se pudo completar la solicitud.";
  }
  if (Array.isArray(payload)) {
    return payload.map(formatApiError).filter(Boolean).join(" ");
  }
  const object = asObject(payload);
  if (!object) return "No se pudo completar la solicitud.";
  if (typeof object.detail === "string") return object.detail;
  return Object.entries(object)
    .flatMap(([field, value]) => {
      const message = formatApiError(value);
      return message ? `${fieldLabel(field)}: ${message}` : [];
    })
    .join(" | ") || "No se pudo completar la solicitud.";
}

async function parseResponse(response: Response): Promise<unknown> {
  if (response.status === 204) return null;
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return "No se pudo procesar la respuesta recibida.";
  }
  try {
    return await response.json();
  } catch {
    return "No se pudo procesar la respuesta recibida.";
  }
}

function kindForStatus(status: number): ApiErrorKind {
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (status === 409) return "conflict";
  if (status >= 400 && status < 500) return "validation";
  return "internal";
}

async function fetchCsrf(): Promise<string> {
  if (csrfToken) return csrfToken;
  if (csrfPromise) return csrfPromise;
  csrfPromise = fetch(`${API_BASE_URL}/auth/csrf/`, {
    credentials: "include",
    headers: { Accept: "application/json" },
  })
    .then(async (response) => {
      const data = asObject(await parseResponse(response));
      if (!response.ok || typeof data?.csrf_token !== "string") {
        throw new ApiError(
          formatApiError(data),
          response.status,
          kindForStatus(response.status),
          data,
        );
      }
      csrfToken = data.csrf_token;
      return csrfToken;
    })
    .catch((error: unknown) => {
      if (error instanceof ApiError) throw error;
      throw new ApiError(
        "No fue posible establecer la conexión.",
        0,
        "network",
      );
    })
    .finally(() => {
      csrfPromise = null;
    });
  return csrfPromise;
}

async function refreshSession(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const token = await fetchCsrf();
      const response = await fetch(`${API_BASE_URL}/auth/refresh/`, {
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-CSRFToken": token,
        },
        body: "{}",
      });
      return response.ok;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

async function execute<T>(path: string, options: RequestOptions): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (UNSAFE_METHODS.has(method)) {
    headers.set("X-CSRFToken", await fetchCsrf());
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      method,
      credentials: "include",
      headers,
    });
  } catch {
    throw new ApiError(
      "No fue posible establecer la conexión. Intente nuevamente.",
      0,
      "network",
    );
  }

  if (response.status === 401 && options.retryAuth !== false) {
    const refreshed = await refreshSession();
    if (refreshed) {
      return execute<T>(path, { ...options, retryAuth: false });
    }
  }

  const data = await parseResponse(response);
  if (!response.ok) {
    if (options.notify !== false) {
      if (response.status === 401) emitSessionEvent("sipeip:unauthorized");
      if (response.status === 403) emitSessionEvent("sipeip:forbidden");
    }
    throw new ApiError(
      formatApiError(data),
      response.status,
      kindForStatus(response.status),
      data,
    );
  }
  if (["/auth/login/", "/auth/logout/"].includes(path)) {
    csrfToken = "";
  }
  return data as T;
}

export function apiRequest<T>(path: string, options: RequestOptions = {}) {
  return execute<T>(path, options);
}

export async function apiDownload(path: string): Promise<Blob> {
  return download(path, true);
}

async function download(path: string, retryAuth: boolean): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      credentials: "include",
      headers: { Accept: "*/*" },
    });
  } catch {
    throw new ApiError("No fue posible establecer la conexión.", 0, "network");
  }

  if (response.status === 401 && retryAuth) {
    const refreshed = await refreshSession();
    if (refreshed) return download(path, false);
  }

  if (!response.ok) {
    const payload = await parseResponse(response);
    if (response.status === 401) emitSessionEvent("sipeip:unauthorized");
    if (response.status === 403) emitSessionEvent("sipeip:forbidden");
    throw new ApiError(
      formatApiError(payload),
      response.status,
      kindForStatus(response.status),
      payload,
    );
  }
  return response.blob();
}

export function normalizeList<T>(payload: T[] | { results: T[] }): T[] {
  return Array.isArray(payload) ? payload : payload.results;
}

export const resourceApi = <T extends ApiRecord>(basePath: string) => ({
  list: async (search = "", filters: Record<string, unknown> = {}) => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    for (const [key, value] of Object.entries(filters)) {
      if (value !== "" && value !== null && value !== undefined) {
        params.set(key, String(value));
      }
    }
    const separator = basePath.includes("?") ? "&" : "?";
    const query = params.size ? `${separator}${params.toString()}` : "";
    const result = await apiRequest<T[] | { results: T[] }>(`${basePath}${query}`);
    return normalizeList(result);
  },
  create: (data: Record<string, unknown>) =>
    apiRequest<T>(basePath, { method: "POST", body: JSON.stringify(data) }),
  update: (id: number, data: Record<string, unknown>) =>
    apiRequest<T>(`${basePath}${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  remove: (id: number) =>
    apiRequest<null>(`${basePath}${id}/`, { method: "DELETE" }),
  action: <R = T>(id: number, action: string, data: Record<string, unknown> = {}) =>
    apiRequest<R>(`${basePath}${id}/${action}/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
});

export const authApi = {
  csrf: fetchCsrf,
  me: <T>() => apiRequest<T>("/auth/me/", { retryAuth: false, notify: false }),
  login: <T>(username: string, password: string) =>
    apiRequest<T>("/auth/login/", {
      method: "POST",
      body: JSON.stringify({ username, password }),
      retryAuth: false,
      notify: false,
    }),
  refresh: <T>() =>
    apiRequest<T>("/auth/refresh/", {
      method: "POST",
      body: "{}",
      retryAuth: false,
      notify: false,
    }),
  logout: () =>
    apiRequest<{ detail: string }>("/auth/logout/", {
      method: "POST",
      body: "{}",
      retryAuth: false,
      notify: false,
    }),
};
