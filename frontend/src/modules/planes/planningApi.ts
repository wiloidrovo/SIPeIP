import { apiRequest } from "../../services/api";
import type {
  IndicatorTracking,
  PlanDossier,
  PlanTracking,
  PlanValidation,
} from "./planningTypes";

export const planningApi = {
  dossier: (planId: number) =>
    apiRequest<PlanDossier>(`/planes/${planId}/expediente/`),
  tracking: (planId: number) =>
    apiRequest<PlanTracking>(`/planes/${planId}/seguimiento/`),
  validation: (planId: number) =>
    apiRequest<PlanValidation>(`/planes/${planId}/validacion/`),
  planAction: <T>(
    planId: number,
    action: string,
    payload: Record<string, unknown> = {},
  ) =>
    apiRequest<T>(`/planes/${planId}/${action}/`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  indicatorTracking: (indicatorId: number) =>
    apiRequest<IndicatorTracking>(
      `/indicadores/${indicatorId}/seguimiento/`,
    ),
  indicatorAction: <T>(
    indicatorId: number,
    action: string,
    payload: Record<string, unknown> = {},
  ) =>
    apiRequest<T>(`/indicadores/${indicatorId}/${action}/`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
