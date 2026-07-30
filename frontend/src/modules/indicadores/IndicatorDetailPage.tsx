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
import { planningApi } from "../planes/planningApi";
import type {
  AlignmentSummary,
  IndicatorAdvance,
  IndicatorTracking,
} from "../planes/planningTypes";

function localDateInputValue() {
  const date = new Date();
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

function dateLabel(value?: string | null, includeTime = false) {
  if (!value) return "Sin dato";
  const source = value.length === 10 ? `${value}T00:00:00` : value;
  const date = new Date(source);
  if (Number.isNaN(date.getTime())) return value;
  return includeTime
    ? date.toLocaleString("es-EC")
    : date.toLocaleDateString("es-EC");
}

function numericLabel(value: number | string | undefined, unit?: string) {
  if (value === undefined || value === "") return "Sin dato";
  const numeric = Number(value);
  const text = Number.isFinite(numeric)
    ? numeric.toLocaleString("es-EC", { maximumFractionDigits: 2 })
    : String(value);
  return unit ? `${text} ${unit}` : text;
}

function pndLabel(alignment: AlignmentSummary) {
  const objective = alignment.objetivo_pnd_detalle ?? alignment.objetivo_pnd;
  if (!objective) return "Sin objetivo PND";
  const axis = objective.eje;
  const objectiveLabel = [objective.codigo, objective.nombre]
    .filter(Boolean)
    .join(" · ");
  const axisLabel = [axis?.codigo, axis?.nombre].filter(Boolean).join(" · ");
  return axisLabel ? `${objectiveLabel} — ${axisLabel}` : objectiveLabel;
}

function AdvancesTable({
  advances,
  unit,
}: {
  advances: IndicatorAdvance[];
  unit?: string;
}) {
  if (!advances.length) {
    return (
      <EmptyState
        title="Sin mediciones registradas"
        detail="El indicador todavía no dispone de una serie histórica."
      />
    );
  }
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Fecha de medición</th>
            <th>Valor</th>
            <th>Observación</th>
            <th>Evidencia</th>
            <th>Registrado por</th>
          </tr>
        </thead>
        <tbody>
          {advances.map((advance) => (
            <tr key={advance.id}>
              <td>{dateLabel(advance.fecha_registro)}</td>
              <td>{numericLabel(advance.valor, unit)}</td>
              <td>{advance.observacion || "Sin observación"}</td>
              <td>{advance.evidencia || "Sin referencia"}</td>
              <td>{advance.registrado_por_detalle?.nombre_completo ?? "Sin dato"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function IndicatorDetailPage() {
  const { indicatorId } = useParams();
  const numericIndicatorId = Number(indicatorId);
  const { hasPermission, user } = useAuth();
  const [data, setData] = useState<IndicatorTracking | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [success, setSuccess] = useState("");
  const [actionMode, setActionMode] = useState<"advance" | "validate" | null>(null);
  const [advanceForm, setAdvanceForm] = useState({
    fecha_registro: localDateInputValue(),
    valor: "",
    observacion: "",
    evidencia: "",
  });

  const load = useCallback(async () => {
    if (!Number.isInteger(numericIndicatorId) || numericIndicatorId < 1) {
      setError("El identificador del indicador no es válido.");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      setData(await planningApi.indicatorTracking(numericIndicatorId));
    } catch (cause) {
      setError(apiErrorMessage(cause));
    } finally {
      setLoading(false);
    }
  }, [numericIndicatorId]);

  useEffect(() => {
    void load();
  }, [load]);

  const advances = useMemo(
    () => data?.avances ?? data?.indicador.avances ?? [],
    [data],
  );
  const alignments = useMemo(
    () => data?.alineaciones ?? data?.indicador.alineaciones ?? [],
    [data],
  );

  function openAdvance() {
    setAdvanceForm({
      fecha_registro: localDateInputValue(),
      valor: "",
      observacion: "",
      evidencia: "",
    });
    setActionMode("advance");
    setActionError("");
  }

  async function submitAction(event: FormEvent) {
    event.preventDefault();
    if (!data || !actionMode) return;
    setBusy(true);
    setActionError("");
    try {
      if (actionMode === "advance") {
        await planningApi.indicatorAction(
          data.indicador.id,
          "registrar-avance",
          {
            fecha_registro: advanceForm.fecha_registro,
            valor: Number(advanceForm.valor),
            observacion: advanceForm.observacion.trim(),
            evidencia: advanceForm.evidencia.trim(),
          },
        );
        setSuccess("El avance se registró y el seguimiento fue actualizado.");
      } else {
        await planningApi.indicatorAction(
          data.indicador.id,
          "validar",
        );
        setSuccess("La ficha técnica del indicador fue validada.");
      }
      setActionMode(null);
      await load();
    } catch (cause) {
      setActionError(apiErrorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingState label="Cargando seguimiento del indicador" />;
  if (!data) {
    return (
      <>
        <PageHeader
          eyebrow="Seguimiento"
          title="Detalle del indicador"
          description="No fue posible preparar la información solicitada."
          actions={<Link className="button button--secondary" to="/indicadores">Volver a indicadores</Link>}
        />
        <Feedback message={error} tone="error" />
      </>
    );
  }

  const { indicador, meta, plan } = data;
  const progress = data.progreso ?? indicador.progreso;
  const status = data.estado_seguimiento ?? indicador.estado_seguimiento;
  const label = data.etiqueta_estado_seguimiento
    ?? indicador.etiqueta_estado_seguimiento;
  const nextMeasurement = data.proxima_medicion ?? indicador.proxima_medicion;
  const lastAdvance = data.ultimo_avance
    ?? indicador.ultimo_avance
    ?? advances[0]
    ?? null;
  const canRegisterAdvance = hasPermission("indicadores.registrar_avance")
    && indicador.activo
    && indicador.validado
    && plan?.estado === "APROBADO";
  const canValidate = hasPermission("indicadores.validar")
    && indicador.activo
    && !indicador.validado
    && plan?.estado === "EN_REVISION_INICIADA"
    && (
      user?.es_superusuario === true
      || plan.revisor === user?.id
      || plan.revisor_detalle?.id === user?.id
    );

  return (
    <>
      <PageHeader
        eyebrow="Seguimiento de indicador"
        title={indicador.nombre}
        description="Consulte cómo las mediciones sustentan el cumplimiento de la meta y su alineación institucional."
        actions={(
          <div className="page-action-group">
            {plan?.id ? (
              <Link className="button button--secondary" to={`/planes/${plan.id}`}>
                Ver expediente del plan
              </Link>
            ) : null}
            <Link className="button button--secondary" to="/indicadores">
              Volver a indicadores
            </Link>
          </div>
        )}
      />
      <Feedback message={error} tone="error" onClose={() => setError("")} />
      <Feedback message={success} tone="success" onClose={() => setSuccess("")} />

      <section className="context-banner indicator-context">
        <div>
          <span>Plan</span>
          <strong>{plan?.nombre ?? "Sin plan"}</strong>
        </div>
        <div>
          <span>Meta</span>
          <strong>{meta?.nombre ?? "Sin meta"}</strong>
        </div>
        <div>
          <span>Estado de cumplimiento</span>
          <strong>{trackingLabel(status, label)}</strong>
        </div>
      </section>

      <section className="panel indicator-summary">
        <div className="panel-title">
          <div>
            <span className="eyebrow">Resultado medido</span>
            <h2>Situación actual</h2>
          </div>
          <OdsBadges value={alignments} />
        </div>
        <p>{indicador.descripcion || "Sin descripción registrada."}</p>
        <div className="indicator-kpis">
          <div><span>Línea base</span><strong>{numericLabel(indicador.valor_base, indicador.unidad_medida)}</strong></div>
          <div><span>Valor actual</span><strong>{numericLabel(indicador.valor_actual, indicador.unidad_medida)}</strong></div>
          <div><span>Valor objetivo</span><strong>{numericLabel(indicador.valor_meta, indicador.unidad_medida)}</strong></div>
          <div><span>Progreso</span><strong>{progress === null || progress === undefined ? "Sin cálculo" : `${Number(progress).toFixed(1)}%`}</strong></div>
        </div>
        <TrackingStatus progress={progress} status={status} label={label} />
      </section>

      <section className="tracking-layout">
        <article className="panel">
          <span className="eyebrow">Calendario de medición</span>
          <h2>Periodicidad</h2>
          <dl className="detail-grid detail-grid--single">
            <div><dt>Frecuencia</dt><dd>{indicador.frecuencia?.replaceAll("_", " ") ?? "Sin definir"}</dd></div>
            <div><dt>Sentido</dt><dd>{indicador.sentido?.replaceAll("_", " ") ?? "Ascendente"}</dd></div>
            <div><dt>Peso en la meta</dt><dd>{numericLabel(indicador.ponderacion, "%")}</dd></div>
            <div><dt>Próxima medición</dt><dd>{dateLabel(nextMeasurement)}</dd></div>
            <div><dt>Última medición</dt><dd>{lastAdvance ? dateLabel(lastAdvance.fecha_registro) : "Sin mediciones"}</dd></div>
            <div><dt>Avance esperado</dt><dd>{indicador.avance_esperado === null || indicador.avance_esperado === undefined ? "Sin cálculo" : `${Number(indicador.avance_esperado).toFixed(1)}%`}</dd></div>
            <div><dt>Tendencia</dt><dd>{indicador.tendencia?.replaceAll("_", " ") ?? "Sin datos"}</dd></div>
            <div><dt>Estado operativo</dt><dd>{indicador.activo ? "Activo" : "Inactivo"}</dd></div>
          </dl>
        </article>
        <article className="panel">
          <span className="eyebrow">Control de calidad</span>
          <h2>Ficha técnica</h2>
          <p>
            {indicador.validado
              ? "La definición del indicador fue revisada y validada."
              : "La ficha está pendiente de validación. Esto no equivale al cumplimiento de la meta."}
          </p>
          <dl className="detail-grid detail-grid--single">
            <div><dt>Validación</dt><dd>{indicador.validado ? "Validada" : "Pendiente"}</dd></div>
            <div><dt>Validado por</dt><dd>{indicador.validado_por_detalle?.nombre_completo ?? "Sin dato"}</dd></div>
            <div><dt>Fecha</dt><dd>{dateLabel(indicador.fecha_validacion, true)}</dd></div>
          </dl>
        </article>
      </section>

      <section className="panel">
        <div className="panel-title">
          <div>
            <span className="eyebrow">Contribución estratégica</span>
            <h2>Alineación PND y ODS</h2>
          </div>
        </div>
        {alignments.length ? (
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
                <strong>{pndLabel(alignment)}</strong>
                <p>{alignment.justificacion || "Sin justificación registrada."}</p>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState
            title="Sin alineación estratégica"
            detail="El objetivo de la meta todavía no dispone de una relación PND/ODS visible."
          />
        )}
      </section>

      <section className="panel">
        <div className="panel-title">
          <div>
            <span className="eyebrow">Serie histórica</span>
            <h2>Avances registrados</h2>
          </div>
          <div className="page-action-group">
            {canValidate ? (
              <button
                className="button button--secondary"
                onClick={() => {
                  setActionError("");
                  setActionMode("validate");
                }}
                type="button"
              >
                Validar ficha
              </button>
            ) : null}
            {canRegisterAdvance ? (
              <button
                className="button button--primary"
                onClick={openAdvance}
                type="button"
              >
                Registrar avance
              </button>
            ) : null}
          </div>
        </div>
        {hasPermission("indicadores.registrar_avance") && !canRegisterAdvance ? (
          <div className="inline-alert inline-alert--warning advance-requirements">
            Para registrar una medición, el indicador debe estar activo y validado,
            y el plan debe encontrarse aprobado.
          </div>
        ) : null}
        <AdvancesTable advances={advances} unit={indicador.unidad_medida} />
      </section>

      <Modal
        open={Boolean(actionMode)}
        onClose={() => setActionMode(null)}
        title={actionMode === "advance" ? "Registrar avance" : "Validar ficha técnica"}
      >
        <form className="resource-form" onSubmit={submitAction}>
          <Feedback
            message={actionError}
            tone="error"
            onClose={() => setActionError("")}
          />
          {actionMode === "advance" ? (
            <>
              <label>
                <span>Fecha de medición *</span>
                <input
                  max={localDateInputValue()}
                  required
                  type="date"
                  value={advanceForm.fecha_registro}
                  onChange={(event) => setAdvanceForm((current) => ({
                    ...current,
                    fecha_registro: event.target.value,
                  }))}
                />
              </label>
              <label>
                <span>Valor alcanzado ({indicador.unidad_medida}) *</span>
                <input
                  min={0}
                  required
                  step="0.01"
                  type="number"
                  value={advanceForm.valor}
                  onChange={(event) => setAdvanceForm((current) => ({
                    ...current,
                    valor: event.target.value,
                  }))}
                />
              </label>
              <label>
                <span>Observación</span>
                <textarea
                  value={advanceForm.observacion}
                  onChange={(event) => setAdvanceForm((current) => ({
                    ...current,
                    observacion: event.target.value,
                  }))}
                />
              </label>
              <label>
                <span>Referencia de evidencia</span>
                <input
                  maxLength={500}
                  placeholder="Documento, enlace o referencia que sustenta la medición"
                  value={advanceForm.evidencia}
                  onChange={(event) => setAdvanceForm((current) => ({
                    ...current,
                    evidencia: event.target.value,
                  }))}
                />
              </label>
            </>
          ) : (
            <div className="inline-alert inline-alert--info">
              Esta acción confirma la calidad de la ficha técnica. El cumplimiento
              de la meta se calcula por separado a partir de sus avances.
            </div>
          )}
          <div className="form-actions">
            <button
              className="button button--secondary"
              disabled={busy}
              onClick={() => setActionMode(null)}
              type="button"
            >
              Cancelar
            </button>
            <button
              className="button button--primary"
              disabled={busy}
              type="submit"
            >
              {busy ? "Procesando…" : "Confirmar"}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
