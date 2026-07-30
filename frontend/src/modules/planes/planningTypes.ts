import type { ApiRecord } from "../../services/api";

export type EntitySummary = {
  id: number;
  codigo_oficial?: string;
  nombre: string;
};

export type UserSummary = {
  id: number;
  username?: string;
  nombre_completo: string;
  email?: string;
};

export type OdsSummary = {
  id: number;
  numero: number | string;
  nombre: string;
};

export type PndAxisSummary = {
  id?: number;
  codigo?: string;
  nombre?: string;
};

export type PndObjectiveSummary = {
  id: number;
  codigo?: string;
  nombre: string;
  eje?: PndAxisSummary | null;
};

export type AlignmentSummary = {
  id: number;
  estado?: string;
  justificacion?: string;
  planes_count?: number;
  metas_count?: number;
  indicadores_count?: number;
  ods?: OdsSummary | null;
  ods_detalle?: OdsSummary | null;
  objetivo_pnd?: PndObjectiveSummary | null;
  objetivo_pnd_detalle?: PndObjectiveSummary | null;
};

export type IndicatorAdvance = {
  id: number;
  fecha_registro: string;
  valor: number | string;
  observacion?: string;
  evidencia?: string;
  registrado_por_detalle?: UserSummary | null;
};

export type IndicatorSummary = {
  id: number;
  nombre: string;
  descripcion?: string;
  unidad_medida: string;
  valor_base: number | string;
  valor_meta: number | string;
  valor_actual: number | string;
  frecuencia?: string;
  sentido?: string;
  ponderacion?: number | string;
  activo: boolean;
  validado: boolean;
  validado_por_detalle?: UserSummary | null;
  fecha_validacion?: string | null;
  progreso?: number | null;
  estado_seguimiento?: string;
  etiqueta_estado_seguimiento?: string;
  proxima_medicion?: string | null;
  avance_esperado?: number | string | null;
  tendencia?: string;
  medicion_atrasada?: boolean;
  ultimo_avance?: IndicatorAdvance | null;
  alineaciones?: AlignmentSummary[];
  avances?: IndicatorAdvance[];
};

export type GoalSummary = {
  id: number;
  nombre: string;
  descripcion?: string;
  resultado_esperado?: string;
  fecha_inicio?: string;
  fecha_fin?: string;
  estado?: string;
  progreso?: number | null;
  estado_seguimiento?: string;
  etiqueta_estado_seguimiento?: string;
  alineaciones?: AlignmentSummary[];
  indicadores?: IndicatorSummary[];
};

export type StrategicObjectiveSummary = {
  id: number;
  codigo?: string;
  nombre: string;
  descripcion?: string;
  estado?: string;
  progreso?: number | null;
  estado_seguimiento?: string;
  etiqueta_estado_seguimiento?: string;
  alineaciones?: AlignmentSummary[];
  metas?: GoalSummary[];
};

export type PlanHistoryItem = {
  id: number;
  fecha: string;
  accion: string;
  estado_anterior?: string;
  estado_nuevo?: string;
  observacion?: string;
  usuario_detalle?: UserSummary | null;
};

export type PlanRecord = ApiRecord & {
  nombre: string;
  descripcion?: string;
  entidad?: number | EntitySummary;
  entidad_detalle?: EntitySummary | null;
  responsable_detalle?: UserSummary | null;
  creado_por_detalle?: UserSummary | null;
  revisor?: number | null;
  revisor_detalle?: UserSummary | null;
  periodo_inicio?: string;
  periodo_fin?: string;
  fecha_creacion?: string;
  fecha_actualizacion?: string;
  estado: string;
  activo?: boolean;
  progreso?: number | null;
  estado_seguimiento?: string;
  etiqueta_estado_seguimiento?: string;
  ods?: OdsSummary[];
  ods_resumen?: OdsSummary[];
  alineaciones?: AlignmentSummary[];
};

export type PlanValidation = {
  completo: boolean;
  listo_para_revision: boolean;
  listo_para_aprobacion: boolean;
  bloqueos: ValidationIssue[];
  advertencias: ValidationIssue[];
};

export type ValidationIssue =
  | string
  | {
      codigo?: string;
      mensaje: string;
      [key: string]: unknown;
    };

export type PlanTrackingSummary = {
  progreso?: number | string | null;
  avance_esperado?: number | string | null;
  estado_seguimiento?: string;
  etiqueta_estado_seguimiento?: string;
  proxima_medicion?: string | null;
  ultimo_avance?: IndicatorAdvance | null;
  objetivos_total?: number;
  metas_total?: number;
  metas_cumplidas?: number;
  metas_en_riesgo?: number;
  metas_pendientes_validacion?: number;
};

export type PlanTracking = {
  plan?: PlanRecord;
  progreso?: number | string | null;
  estado_seguimiento?: string;
  etiqueta_estado_seguimiento?: string;
  ultima_actualizacion?: string | null;
  resumen?: PlanTrackingSummary;
  total_objetivos?: number;
  total_metas?: number;
  total_indicadores?: number;
  indicadores_cumplidos?: number;
  indicadores_en_riesgo?: number;
  indicadores_atrasados?: number;
  proximos_vencimientos?: number;
  objetivos?: StrategicObjectiveSummary[];
  metas?: GoalSummary[];
};

export type PlanDossier = {
  plan: PlanRecord;
  validacion: PlanValidation;
  progreso?: number | string | null;
  estado_seguimiento?: string;
  etiqueta_estado_seguimiento?: string;
  resumen?: PlanTrackingSummary;
  objetivos: StrategicObjectiveSummary[];
  historial: PlanHistoryItem[];
  seguimiento?: PlanTracking | null;
};

export type IndicatorTracking = {
  indicador: IndicatorSummary;
  meta?: GoalSummary | null;
  plan?: PlanRecord | null;
  alineaciones?: AlignmentSummary[];
  avances?: IndicatorAdvance[];
  progreso?: number | null;
  estado_seguimiento?: string;
  etiqueta_estado_seguimiento?: string;
  proxima_medicion?: string | null;
  ultimo_avance?: IndicatorAdvance | null;
};
