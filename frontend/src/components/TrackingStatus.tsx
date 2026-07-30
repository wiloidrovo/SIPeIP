import type { ReactNode } from "react";
import type {
  AlignmentSummary,
  OdsSummary,
} from "../modules/planes/planningTypes";

const STATUS_LABELS: Record<string, string> = {
  SIN_DATOS: "Sin datos",
  SIN_AVANCES: "Sin avances",
  SIN_MEDICION: "Sin medición",
  PENDIENTE: "Pendiente",
  PENDIENTE_VALIDACION: "Pendiente de validación",
  EN_CURSO: "En curso",
  EN_PROGRESO: "En progreso",
  AL_DIA: "Al día",
  CUMPLIDO: "Cumplido",
  EN_RIESGO: "En riesgo",
  ATRASADO: "Atrasado",
  INCUMPLIDO: "Incumplido",
  NO_APLICA: "No aplica",
};

function normalizedStatus(value?: string) {
  return String(value ?? "SIN_DATOS").trim().toUpperCase();
}

export function trackingLabel(code?: string, explicitLabel?: string) {
  if (explicitLabel?.trim()) return explicitLabel;
  const normalized = normalizedStatus(code);
  return STATUS_LABELS[normalized]
    ?? normalized.replaceAll("_", " ").toLocaleLowerCase("es-EC")
      .replace(/^./, (character) => character.toUpperCase());
}

function statusTone(code?: string) {
  const normalized = normalizedStatus(code);
  if (["CUMPLIDO", "AL_DIA"].includes(normalized)) return "success";
  if (["EN_RIESGO", "ATRASADO", "INCUMPLIDO"].includes(normalized)) {
    return "danger";
  }
  if (["EN_PROGRESO", "EN_CURSO", "PENDIENTE", "PENDIENTE_VALIDACION"].includes(normalized)) return "warning";
  return "neutral";
}

export function clampProgress(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return null;
  return Math.min(100, Math.max(0, numeric));
}

export function TrackingStatus({
  progress,
  status,
  label,
  compact = false,
}: {
  progress?: unknown;
  status?: string;
  label?: string;
  compact?: boolean;
}) {
  const numeric = clampProgress(progress);
  const readableLabel = trackingLabel(status, label);
  const tone = statusTone(status);
  return (
    <div className={`tracking-status${compact ? " tracking-status--compact" : ""}`}>
      <div className="tracking-status__header">
        <span className={`status-badge status-badge--${tone}`}>
          {readableLabel}
        </span>
        <strong>{numeric === null ? "Sin cálculo" : `${numeric.toFixed(1)}%`}</strong>
      </div>
      <div
        className="progress-track"
        role="progressbar"
        aria-label={`Cumplimiento: ${readableLabel}`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={numeric ?? 0}
        aria-valuetext={numeric === null ? "Sin cálculo disponible" : `${numeric.toFixed(1)} por ciento`}
      >
        <span style={{ width: `${numeric ?? 0}%` }} />
      </div>
    </div>
  );
}

function asObject(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function extractOds(value: unknown): OdsSummary[] {
  if (!Array.isArray(value)) return [];
  const byId = new Map<string, OdsSummary>();
  for (const item of value) {
    const record = asObject(item);
    if (!record) continue;
    const nested = asObject(record.ods) ?? asObject(record.ods_detalle) ?? record;
    const id = Number(nested.id);
    const numero = nested.numero;
    const nombre = String(nested.nombre ?? "").trim();
    if (!Number.isFinite(id) || numero === undefined || !nombre) continue;
    byId.set(String(id), { id, numero: String(numero), nombre });
  }
  return [...byId.values()];
}

export function OdsBadges({
  value,
  empty = "Sin ODS asociado",
}: {
  value: unknown;
  empty?: ReactNode;
}) {
  const odsItems = extractOds(value);
  if (!odsItems.length) return <span className="muted">{empty}</span>;
  return (
    <span className="tag-list" aria-label="ODS asociados">
      {odsItems.map((ods) => (
        <span className="data-tag" key={ods.id} title={ods.nombre}>
          ODS {ods.numero}
        </span>
      ))}
    </span>
  );
}

export function alignmentOds(
  alignments?: AlignmentSummary[],
): AlignmentSummary[] {
  return alignments ?? [];
}
