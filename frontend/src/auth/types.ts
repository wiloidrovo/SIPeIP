export type SessionRole = {
  id: number;
  codigo: string;
  nombre: string;
  activo: boolean;
  alcance: string;
};

export type SessionEntity = {
  id: number;
  codigo_oficial: string;
  nombre: string;
};

export type SessionUser = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  nombre_completo: string;
  estado: string;
  rol: SessionRole | null;
  permisos: string[];
  institucion: SessionEntity | null;
  unidad: { id: number; codigo: string; nombre: string } | null;
  es_superusuario: boolean;
};

export type SessionResponse = {
  detail: string;
  usuario: SessionUser;
  expira_en_segundos: number;
};
