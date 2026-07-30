import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { EmptyState, Feedback, LoadingState } from "../../components/States";
import {
  OdsBadges,
  TrackingStatus,
  trackingLabel,
} from "../../components/TrackingStatus";
import { apiErrorMessage } from "../../components/ResourcePage";
import { planningApi } from "./planningApi";
import type {
  AlignmentSummary,
  GoalSummary,
  IndicatorSummary,
  PlanDossier,
  PlanHistoryItem,
  PlanTracking,
  PlanValidation,
  ValidationIssue,
  StrategicObjectiveSummary,
} from "./planningTypes";

type ReviewAction = {
  endpoint: "enviar-a-revision" | "revisar" | "devolver" | "aprobar" | "rechazar";
  label: string;
  permission: string;
  tone: "primary" | "secondary" | "danger";
  requiresObservation?: boolean;
  requiresReviewConfirmation?: boolean;
};

const REVIEW_ACTIONS: ReviewAction[] = [
  {
    endpoint: "enviar-a-revision",
    label: "Enviar a revisión",
    permission: "planes.enviar_revision",
    tone: "primary",
  },
  {
    endpoint: "revisar",
    label: "Iniciar revisión",
    permission: "planes.revisar",
    tone: "primary",
  },
  {
    endpoint: "devolver",
    label: "Devolver para corrección",
    permission: "planes.devolver",
    tone: "secondary",
    requiresObservation: true,
    requiresReviewConfirmation: true,
  },
  {
    endpoint: "aprobar",
    label: "Aprobar plan",
    permission: "planes.aprobar",
    tone: "primary",
    requiresReviewConfirmation: true,
  },
  {
    endpoint: "rechazar",
    label: "Rechazar plan",
    permission: "planes.rechazar",
    tone: "danger",
    requiresObservation: true,
    requiresReviewConfirmation: true,
  },
];

const ACTION_STATES: Record<ReviewAction["endpoint"], string[]> = {
  "enviar-a-revision": ["BORRADOR", "DEVUELTO", "RECHAZADO"],
  revisar: ["EN_REVISION"],
  devolver: ["EN_REVISION_INICIADA"],
  aprobar: ["EN_REVISION_INICIADA"],
  rechazar: ["EN_REVISION_INICIADA"],
};

function dateLabel(value?: string | null, includeTime = false) {
  if (!value) return "Sin dato";
  const source = value.length === 10 ? `${value}T00:00:00` : value;
  const date = new Date(source);
  if (Number.isNaN(date.getTime())) return value;
  return includeTime
    ? date.toLocaleString("es-EC")
    : date.toLocaleDateString("es-EC");
}

function numberLabel(value: number | string | undefined, unit?: string) {
  if (value === undefined || value === "") return "Sin dato";
  const numeric = Number(value);
  const formatted = Number.isFinite(numeric)
    ? numeric.toLocaleString("es-EC", { maximumFractionDigits: 2 })
    : String(value);
  return unit ? `${formatted} ${unit}` : formatted;
}

function alignmentPnd(alignment: AlignmentSummary) {
  const objective = alignment.objetivo_pnd_detalle ?? alignment.objetivo_pnd;
  if (!objective) return "Sin objetivo PND";
  const axis = objective.eje;
  const objectiveText = [objective.codigo, objective.nombre]
    .filter(Boolean)
    .join(" · ");
  const axisText = [axis?.codigo, axis?.nombre].filter(Boolean).join(" · ");
  return axisText ? `${objectiveText} — ${axisText}` : objectiveText;
}

function AlignmentList({
  alignments,
}: {
  alignments?: AlignmentSummary[];
}) {
  if (!alignments?.length) {
    return (
      <div className="inline-alert inline-alert--warning">
        Este objetivo todavía no tiene una alineación PND/ODS registrada.
      </div>
    );
  }
  return (
    <div className="alignment-list">
      {alignments.map((alignment) => (
        <article className="alignment-card" key={alignment.id}>
          <div className="alignment-card__heading">
            <OdsBadges value={[alignment]} />
            {alignment.estado ? (
              <span className="status-badge status-badge--neutral">
                {alignment.estado.replaceAll("_", " ")}
              </span>
            ) : null}
          </div>
          <strong>{alignmentPnd(alignment)}</strong>
          <p>{alignment.justificacion || "Sin justificación registrada."}</p>
        </article>
      ))}
    </div>
  );
}

function IndicatorCard({ indicator }: { indicator: IndicatorSummary }) {
  const latest = indicator.ultimo_avance
    ?? indicator.avances?.[0]
    ?? null;
  return (
    <article className="indicator-card">
      <div className="indicator-card__heading">
        <div>
          <h5>{indicator.nombre}</h5>
          <p>{indicator.descripcion || "Sin descripción."}</p>
        </div>
        <Link
          className="link-button"
          to={`/indicadores/${indicator.id}`}
          aria-label={`Abrir seguimiento del indicador ${indicator.nombre}`}
        >
          Ver seguimiento
        </Link>
      </div>
      <div className="indicator-values">
        <div><span>Línea base</span><strong>{numberLabel(indicator.valor_base, indicator.unidad_medida)}</strong></div>
        <div><span>Valor actual</span><strong>{numberLabel(indicator.valor_actual, indicator.unidad_medida)}</strong></div>
        <div><span>Valor objetivo</span><strong>{numberLabel(indicator.valor_meta, indicator.unidad_medida)}</strong></div>
        <div><span>Última medición</span><strong>{latest ? dateLabel(latest.fecha_registro) : "Sin mediciones"}</strong></div>
      </div>
      <TrackingStatus
        progress={indicator.progreso}
        status={indicator.estado_seguimiento}
        label={indicator.etiqueta_estado_seguimiento}
      />
      <div className="indicator-meta">
        <span>Frecuencia: <strong>{indicator.frecuencia?.toLocaleLowerCase("es-EC") ?? "sin definir"}</strong></span>
        <span>Sentido: <strong>{indicator.sentido?.toLocaleLowerCase("es-EC") ?? "ascendente"}</strong></span>
        <span>Peso: <strong>{numberLabel(indicator.ponderacion, "%")}</strong></span>
        <span>Próxima medición: <strong>{dateLabel(indicator.proxima_medicion)}</strong></span>
        <span>Ficha: <strong>{indicator.validado ? "validada" : "pendiente de validación"}</strong></span>
      </div>
    </article>
  );
}

function GoalPanel({ goal }: { goal: GoalSummary }) {
  const indicators = goal.indicadores ?? [];
  return (
    <section className="goal-panel">
      <div className="goal-panel__heading">
        <div>
          <span className="eyebrow">Meta</span>
          <h4>{goal.nombre}</h4>
          <p>{goal.resultado_esperado || goal.descripcion || "Sin resultado esperado registrado."}</p>
        </div>
        <TrackingStatus
          compact
          progress={goal.progreso}
          status={goal.estado_seguimiento}
          label={goal.etiqueta_estado_seguimiento}
        />
      </div>
      <dl className="goal-dates">
        <div><dt>Inicio</dt><dd>{dateLabel(goal.fecha_inicio)}</dd></div>
        <div><dt>Vencimiento</dt><dd>{dateLabel(goal.fecha_fin)}</dd></div>
        <div><dt>Estado</dt><dd>{goal.estado?.replaceAll("_", " ") ?? "Sin dato"}</dd></div>
        <div><dt>Indicadores</dt><dd>{indicators.length}</dd></div>
      </dl>
      {indicators.length ? (
        <div className="indicator-grid">
          {indicators.map((indicator) => (
            <IndicatorCard indicator={indicator} key={indicator.id} />
          ))}
        </div>
      ) : (
        <div className="inline-alert inline-alert--warning">
          La meta no tiene indicadores para demostrar su cumplimiento.
        </div>
      )}
    </section>
  );
}

function ObjectivePanel({
  objective,
  index,
}: {
  objective: StrategicObjectiveSummary;
  index: number;
}) {
  return (
    <details className="objective-panel" open={index === 0}>
      <summary>
        <span>
          <small>Objetivo estratégico</small>
          <strong>
            {[objective.codigo, objective.nombre].filter(Boolean).join(" · ")}
          </strong>
        </span>
        <TrackingStatus
          compact
          progress={objective.progreso}
          status={objective.estado_seguimiento}
          label={objective.etiqueta_estado_seguimiento}
        />
      </summary>
      <div className="objective-panel__content">
        {objective.descripcion ? <p>{objective.descripcion}</p> : null}
        <section aria-label={`Alineaciones de ${objective.nombre}`}>
          <h3 className="subsection-title">Alineación nacional y ODS</h3>
          <AlignmentList alignments={objective.alineaciones} />
        </section>
        <section aria-label={`Metas de ${objective.nombre}`}>
          <h3 className="subsection-title">Metas e indicadores</h3>
          {objective.metas?.length ? (
            <div className="goal-list">
              {objective.metas.map((goal) => (
                <GoalPanel goal={goal} key={goal.id} />
              ))}
            </div>
          ) : (
            <div className="inline-alert inline-alert--warning">
              Este objetivo no contiene metas dentro del plan.
            </div>
          )}
        </section>
      </div>
    </details>
  );
}

function ValidationPanel({ validation }: { validation: PlanValidation }) {
  const issueMessage = (issue: ValidationIssue) =>
    typeof issue === "string" ? issue : issue.mensaje;
  const issueKey = (issue: ValidationIssue, index: number) =>
    typeof issue === "string"
      ? `${index}-${issue}`
      : `${issue.codigo ?? index}-${issue.mensaje}`;
  const tone = validation.listo_para_aprobacion ? "success" : "warning";
  return (
    <section className={`panel validation-panel validation-panel--${tone}`}>
      <div className="panel-title">
        <div>
          <span className="eyebrow">Validación del expediente</span>
          <h2>
            {validation.listo_para_aprobacion
              ? "El plan está listo para decisión"
              : "El plan requiere revisión"}
          </h2>
        </div>
        <span
          className={`status-badge status-badge--${validation.completo ? "success" : "warning"}`}
        >
          {validation.completo ? "ESTRUCTURA COMPLETA" : "INFORMACIÓN PENDIENTE"}
        </span>
      </div>
      {validation.bloqueos.length ? (
        <div className="validation-group validation-group--danger">
          <h3>Bloqueos</h3>
          <ul>{validation.bloqueos.map((item, index) => <li key={issueKey(item, index)}>{issueMessage(item)}</li>)}</ul>
        </div>
      ) : null}
      {validation.advertencias.length ? (
        <div className="validation-group validation-group--warning">
          <h3>Advertencias</h3>
          <ul>{validation.advertencias.map((item, index) => <li key={issueKey(item, index)}>{issueMessage(item)}</li>)}</ul>
        </div>
      ) : null}
      {!validation.bloqueos.length && !validation.advertencias.length ? (
        <p className="validation-ok">
          La estructura del plan, sus metas, indicadores y alineaciones no presentan observaciones pendientes.
        </p>
      ) : null}
    </section>
  );
}

function TrackingSummary({
  dossier,
  tracking,
}: {
  dossier: PlanDossier;
  tracking: PlanTracking;
}) {
  const progress = tracking.progreso ?? dossier.progreso ?? dossier.plan.progreso;
  const status = tracking.estado_seguimiento
    ?? dossier.estado_seguimiento
    ?? dossier.plan.estado_seguimiento;
  const label = tracking.etiqueta_estado_seguimiento
    ?? dossier.etiqueta_estado_seguimiento
    ?? dossier.plan.etiqueta_estado_seguimiento;
  const summary = tracking.resumen ?? dossier.resumen ?? {};
  const objectives = tracking.objetivos ?? dossier.objetivos;
  const indicatorsTotal = objectives.reduce(
    (objectiveTotal, objective) =>
      objectiveTotal
      + (objective.metas ?? []).reduce(
        (goalTotal, goal) => goalTotal + (goal.indicadores?.length ?? 0),
        0,
      ),
    0,
  );
  const metrics = [
    ["Objetivos", summary.objetivos_total ?? tracking.total_objetivos],
    ["Metas", summary.metas_total ?? tracking.total_metas],
    ["Indicadores", tracking.total_indicadores ?? indicatorsTotal],
    ["Metas cumplidas", summary.metas_cumplidas],
    ["Metas en riesgo", summary.metas_en_riesgo],
    ["Próxima medición", dateLabel(summary.proxima_medicion)],
  ] as const;
  return (
    <section className="panel plan-tracking-summary">
      <div className="plan-tracking-summary__main">
        <div>
          <span className="eyebrow">Seguimiento consolidado</span>
          <h2>{trackingLabel(status, label)}</h2>
          <p>
            Última actualización: {dateLabel(tracking.ultima_actualizacion ?? dossier.plan.fecha_actualizacion, true)}
          </p>
        </div>
        <TrackingStatus progress={progress} status={status} label={label} />
      </div>
      <div className="tracking-metrics">
        {metrics.map(([metricLabel, value]) => (
          <div key={metricLabel}>
            <span>{metricLabel}</span>
            <strong>{value ?? 0}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

function HistoryTable({ history }: { history: PlanHistoryItem[] }) {
  if (!history.length) {
    return (
      <EmptyState
        title="Sin transiciones registradas"
        detail="El historial aparecerá cuando el plan avance dentro del flujo institucional."
      />
    );
  }
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Acción</th>
            <th>Transición</th>
            <th>Responsable</th>
            <th>Observación</th>
          </tr>
        </thead>
        <tbody>
          {history.map((item) => (
            <tr key={item.id}>
              <td>{dateLabel(item.fecha, true)}</td>
              <td>{item.accion.replaceAll("_", " ")}</td>
              <td>
                {item.estado_anterior?.replaceAll("_", " ") ?? "—"}
                {" → "}
                {item.estado_nuevo?.replaceAll("_", " ") ?? "—"}
              </td>
              <td>{item.usuario_detalle?.nombre_completo ?? "Sistema"}</td>
              <td>{item.observacion || "Sin observación"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function PlanDetailPage() {
  const { planId } = useParams();
  const numericPlanId = Number(planId);
  const { hasPermission, user } = useAuth();
  const [dossier, setDossier] = useState<PlanDossier | null>(null);
  const [tracking, setTracking] = useState<PlanTracking | null>(null);
  const [validation, setValidation] = useState<PlanValidation | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [success, setSuccess] = useState("");
  const [selectedAction, setSelectedAction] = useState<ReviewAction | null>(null);
  const [observation, setObservation] = useState("");
  const [reviewConfirmed, setReviewConfirmed] = useState(false);

  const load = useCallback(async () => {
    if (!Number.isInteger(numericPlanId) || numericPlanId < 1) {
      setError("El identificador del plan no es válido.");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const dossierResponse = await planningApi.dossier(numericPlanId);
      setDossier(dossierResponse);
      setTracking({
        progreso: dossierResponse.progreso,
        estado_seguimiento: dossierResponse.estado_seguimiento,
        etiqueta_estado_seguimiento:
          dossierResponse.etiqueta_estado_seguimiento,
        resumen: dossierResponse.resumen,
        objetivos: dossierResponse.objetivos,
      });
      setValidation(dossierResponse.validacion);
    } catch (cause) {
      setError(apiErrorMessage(cause));
    } finally {
      setLoading(false);
    }
  }, [numericPlanId]);

  useEffect(() => {
    void load();
  }, [load]);

  const availableActions = useMemo(() => {
    const state = dossier?.plan.estado;
    if (!state) return [];
    const reviewerId = dossier.plan.revisor_detalle?.id;
    return REVIEW_ACTIONS.filter(
      (action) =>
        hasPermission(action.permission)
        && ACTION_STATES[action.endpoint].includes(state),
    ).filter(
      (action) =>
        !["devolver", "aprobar", "rechazar"].includes(action.endpoint)
        || reviewerId === user?.id
        || user?.es_superusuario === true,
    );
  }, [dossier, hasPermission, user?.es_superusuario, user?.id]);

  function openAction(action: ReviewAction) {
    setSelectedAction(action);
    setObservation("");
    setReviewConfirmed(false);
    setActionError("");
  }

  async function submitAction(event: FormEvent) {
    event.preventDefault();
    if (!selectedAction || !dossier) return;
    if (selectedAction.requiresObservation && !observation.trim()) {
      setActionError("Debe registrar una observación que sustente la decisión.");
      return;
    }
    if (selectedAction.requiresReviewConfirmation && !reviewConfirmed) {
      setActionError("Confirme que revisó el expediente completo antes de decidir.");
      return;
    }
    setBusy(true);
    setActionError("");
    try {
      await planningApi.planAction(
        dossier.plan.id,
        selectedAction.endpoint,
        observation.trim() ? { observacion: observation.trim() } : {},
      );
      setSelectedAction(null);
      setSuccess(`La acción «${selectedAction.label}» se completó correctamente.`);
      await load();
    } catch (cause) {
      setActionError(apiErrorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingState label="Cargando expediente del plan" />;
  if (!dossier || !validation || !tracking) {
    return (
      <>
        <PageHeader
          eyebrow="Planificación"
          title="Expediente del plan"
          description="No fue posible preparar la información solicitada."
          actions={<Link className="button button--secondary" to="/planes">Volver a planes</Link>}
        />
        <Feedback message={error} tone="error" />
      </>
    );
  }

  const { plan } = dossier;
  const planEntity = plan.entidad_detalle
    ?? (
      plan.entidad !== null
      && typeof plan.entidad === "object"
        ? plan.entidad
        : null
    );
  const progress = tracking.progreso ?? dossier.progreso ?? plan.progreso;
  const trackingState = tracking.estado_seguimiento
    ?? dossier.estado_seguimiento
    ?? plan.estado_seguimiento;
  const trackingStateLabel = tracking.etiqueta_estado_seguimiento
    ?? dossier.etiqueta_estado_seguimiento
    ?? plan.etiqueta_estado_seguimiento;
  const reviewAssignedToAnotherUser = plan.estado === "EN_REVISION_INICIADA"
    && Boolean(plan.revisor_detalle?.id)
    && plan.revisor_detalle?.id !== user?.id
    && user?.es_superusuario !== true
    && ["planes.devolver", "planes.aprobar", "planes.rechazar"].some(hasPermission);

  return (
    <>
      <PageHeader
        eyebrow="Expediente institucional"
        title={plan.nombre}
        description="Revise la estructura, alineación, metas, indicadores, avances e historial antes de tomar una decisión."
        actions={<Link className="button button--secondary" to="/planes">Volver a planes</Link>}
      />
      <Feedback
        message={error}
        tone="error"
        onClose={() => setError("")}
      />
      <Feedback
        message={success}
        tone="success"
        onClose={() => setSuccess("")}
      />

      <section className="context-banner plan-context">
        <div>
          <span>Entidad</span>
          <strong>{planEntity?.nombre ?? "Sin entidad"}</strong>
        </div>
        <div>
          <span>Estado del flujo</span>
          <strong>{plan.estado.replaceAll("_", " ")}</strong>
        </div>
        <div>
          <span>Seguimiento</span>
          <strong>{trackingLabel(trackingState, trackingStateLabel)}</strong>
        </div>
      </section>

      <ValidationPanel validation={validation} />

      <section className="panel plan-overview">
        <div className="panel-title">
          <div>
            <span className="eyebrow">Información general</span>
            <h2>Contenido presentado</h2>
          </div>
          <OdsBadges
            value={
              plan.alineaciones
              ?? plan.ods_resumen
              ?? plan.ods
              ?? dossier.objetivos.flatMap((objective) => objective.alineaciones ?? [])
            }
          />
        </div>
        <p className="plan-description">
          {plan.descripcion || "El plan no tiene una descripción registrada."}
        </p>
        <dl className="detail-grid">
          <div><dt>Responsable</dt><dd>{plan.responsable_detalle?.nombre_completo ?? "Sin responsable"}</dd></div>
          <div><dt>Creado por</dt><dd>{plan.creado_por_detalle?.nombre_completo ?? "Sin dato"}</dd></div>
          <div><dt>Revisor</dt><dd>{plan.revisor_detalle?.nombre_completo ?? "Aún no asignado"}</dd></div>
          <div><dt>Periodo</dt><dd>{dateLabel(plan.periodo_inicio)} — {dateLabel(plan.periodo_fin)}</dd></div>
        </dl>
        <TrackingStatus
          progress={progress}
          status={trackingState}
          label={trackingStateLabel}
        />
      </section>

      <TrackingSummary dossier={dossier} tracking={tracking} />

      <section className="plan-content" aria-labelledby="plan-content-title">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Cadena de resultados</span>
            <h2 id="plan-content-title">Objetivos, alineación, metas e indicadores</h2>
          </div>
          <span className="record-count">
            {dossier.objetivos.length} objetivo{dossier.objetivos.length === 1 ? "" : "s"}
          </span>
        </div>
        {dossier.objetivos.length ? (
          <div className="objective-list">
            {dossier.objetivos.map((objective, index) => (
              <ObjectivePanel
                objective={objective}
                index={index}
                key={objective.id}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            title="El plan no contiene objetivos"
            detail="No es posible sustentar una decisión sin objetivos, metas e indicadores asociados."
          />
        )}
      </section>

      <section className="panel">
        <div className="panel-title">
          <div>
            <span className="eyebrow">Trazabilidad</span>
            <h2>Historial de decisiones</h2>
          </div>
        </div>
        <HistoryTable history={dossier.historial ?? []} />
      </section>

      {reviewAssignedToAnotherUser ? (
        <div className="inline-alert inline-alert--warning review-assignment-alert">
          La revisión fue iniciada por {plan.revisor_detalle?.nombre_completo}.
          Solo esa persona puede resolverla mientras permanezca asignada.
        </div>
      ) : null}

      {availableActions.length ? (
        <section className="panel decision-panel" aria-labelledby="decision-title">
          <div>
            <span className="eyebrow">Decisión institucional</span>
            <h2 id="decision-title">Resolver el expediente</h2>
            <p>
              Las acciones disponibles corresponden al estado actual y a sus permisos efectivos.
              La aprobación solo se habilita cuando el expediente cumple las validaciones institucionales.
            </p>
          </div>
          <div className="decision-panel__actions">
            {availableActions.map((action) => {
              const disabled = action.endpoint === "aprobar"
                ? !validation.listo_para_aprobacion
                : action.endpoint === "enviar-a-revision"
                  ? !validation.listo_para_revision
                  : false;
              return (
                <button
                  className={`button button--${action.tone}`}
                  disabled={disabled}
                  key={action.endpoint}
                  onClick={() => openAction(action)}
                  type="button"
                  title={disabled ? "El expediente mantiene bloqueos pendientes." : undefined}
                >
                  {action.label}
                </button>
              );
            })}
          </div>
        </section>
      ) : null}

      <Modal
        open={Boolean(selectedAction)}
        onClose={() => setSelectedAction(null)}
        title={selectedAction?.label ?? "Confirmar acción"}
      >
        <form className="resource-form" onSubmit={submitAction}>
          <Feedback
            message={actionError}
            tone="error"
            onClose={() => setActionError("")}
          />
          <p className="dialog-detail">
            Esta decisión quedará registrada en el historial institucional del plan.
          </p>
          {selectedAction?.requiresObservation ? (
            <label>
              <span>Motivo u observación *</span>
              <textarea
                required
                value={observation}
                onChange={(event) => setObservation(event.target.value)}
              />
            </label>
          ) : selectedAction?.endpoint === "aprobar" ? (
            <label>
              <span>Observación de aprobación</span>
              <textarea
                value={observation}
                onChange={(event) => setObservation(event.target.value)}
              />
            </label>
          ) : null}
          {selectedAction?.requiresReviewConfirmation ? (
            <label className="checkbox-field review-confirmation">
              <input
                checked={reviewConfirmed}
                onChange={(event) => setReviewConfirmed(event.target.checked)}
                type="checkbox"
              />
              <span>
                Confirmo que revisé la descripción, los objetivos, las alineaciones,
                las metas, los indicadores, los avances y las observaciones del expediente.
              </span>
            </label>
          ) : null}
          <div className="form-actions">
            <button
              className="button button--secondary"
              disabled={busy}
              onClick={() => setSelectedAction(null)}
              type="button"
            >
              Cancelar
            </button>
            <button
              className={`button button--${selectedAction?.tone ?? "primary"}`}
              disabled={busy}
              type="submit"
            >
              {busy ? "Procesando…" : "Confirmar decisión"}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
