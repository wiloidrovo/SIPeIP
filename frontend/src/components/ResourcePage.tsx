import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";
import { ApiError, apiRequest, normalizeList, resourceApi } from "../services/api";
import type { ApiRecord } from "../services/api";
import { ConfirmDialog, Modal } from "./Modal";
import { EmptyState, Feedback, LoadingState } from "./States";
import { PageHeader } from "./PageHeader";

export type SelectOption = {
  value: string | number;
  label: string;
  disabled?: boolean;
};
export type ResourceField = {
  name: string;
  label: string;
  type?: "text" | "email" | "password" | "textarea" | "date" | "number" | "select" | "checkbox";
  required?: boolean;
  placeholder?: string;
  options?: SelectOption[];
  loadOptions?: (record?: ApiRecord) => Promise<SelectOption[]>;
  emptyAsNull?: boolean;
  createOnly?: boolean;
  readOnlyOnEdit?: boolean;
  min?: number;
  max?: number;
  step?: string;
};

export type ResourceColumn = {
  key: string;
  label: string;
  render?: (record: ApiRecord) => ReactNode;
};

export type ResourceAction = {
  key: string;
  label: string;
  permission: string;
  allPermissions?: string[];
  endpoint?: string;
  states?: string[];
  stateField?: string;
  confirm?: string;
  tone?: "default" | "danger" | "success";
  payload?: (record: ApiRecord) => Record<string, unknown> | null;
  formFields?: ResourceField[];
  method?: "GET" | "POST";
  resultTitle?: string;
  renderResult?: (result: unknown) => ReactNode;
  canRun?: (record: ApiRecord) => boolean;
};

export type ResourcePageProps = {
  title: string;
  eyebrow?: string;
  description: string;
  apiPath: string;
  columns: ResourceColumn[];
  fields?: ResourceField[];
  viewPermission: string;
  createPermission?: string;
  editPermission?: string;
  deletePermission?: string;
  actions?: ResourceAction[];
  filters?: ResourceField[];
  initialValues?: Record<string, unknown>;
  preparePayload?: (data: Record<string, unknown>, editing: ApiRecord | null) => Record<string, unknown>;
  canEdit?: (record: ApiRecord) => boolean;
  canDelete?: (record: ApiRecord) => boolean;
  deleteWarning?: (record: ApiRecord) => string;
  extraContent?: ReactNode;
};

function getPath(record: ApiRecord, path: string): unknown {
  return path.split(".").reduce<unknown>((value, key) => {
    if (!value || typeof value !== "object") return undefined;
    return (value as Record<string, unknown>)[key];
  }, record);
}

function displayValue(value: unknown): ReactNode {
  if (value === true) return <span className="status-badge status-badge--success">Sí</span>;
  if (value === false) return <span className="status-badge status-badge--neutral">No</span>;
  if (value === null || value === undefined || value === "") return <span className="muted">Sin dato</span>;
  if (typeof value === "object") return <span className="muted">Información disponible</span>;
  const text = String(value);
  if (["ACTIVO", "ACTIVA", "APROBADO", "VALIDADA", "EN_EJECUCION"].includes(text)) {
    return <span className="status-badge status-badge--success">{text.replaceAll("_", " ")}</span>;
  }
  if (["BLOQUEADO", "INACTIVO", "INACTIVA", "RECHAZADO", "RECHAZADA", "SUSPENDIDO"].includes(text)) {
    return <span className="status-badge status-badge--danger">{text.replaceAll("_", " ")}</span>;
  }
  if (["BORRADOR", "EN_REVISION", "PLANIFICADO"].includes(text)) {
    return <span className="status-badge status-badge--warning">{text.replaceAll("_", " ")}</span>;
  }
  return text;
}

function humanizeKey(value: string) {
  const text = value.replaceAll("_", " ").trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : "Detalle";
}

function structuredValue(value: unknown): ReactNode {
  if (Array.isArray(value)) {
    if (!value.length) return <span className="muted">Sin información</span>;
    return (
      <div className="structured-list">
        {value.map((item, index) => (
          <div className="structured-list__item" key={index}>
            {structuredValue(item)}
          </div>
        ))}
      </div>
    );
  }
  if (value !== null && typeof value === "object") {
    return (
      <dl className="structured-result">
        {Object.entries(value as Record<string, unknown>).map(([key, item]) => (
          <div key={key}>
            <dt>{humanizeKey(key)}</dt>
            <dd>{structuredValue(item)}</dd>
          </div>
        ))}
      </dl>
    );
  }
  return displayValue(value);
}

export function ResourcePage(props: ResourcePageProps) {
  const { hasPermission, hasAllPermissions, user } = useAuth();
  const api = useMemo(() => resourceApi<ApiRecord>(props.apiPath), [props.apiPath]);
  const [records, setRecords] = useState<ApiRecord[]>([]);
  const [search, setSearch] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<ApiRecord | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState<Record<string, unknown>>(props.initialValues ?? {});
  const [options, setOptions] = useState<Record<string, SelectOption[]>>({});
  const [feedback, setFeedback] = useState<{ text: string; tone: "success" | "error" | "info" }>({ text: "", tone: "info" });
  const [confirmation, setConfirmation] = useState<{ kind: "delete" | "action"; record: ApiRecord; action?: ResourceAction } | null>(null);
  const [actionForm, setActionForm] = useState<{ record: ApiRecord; action: ResourceAction } | null>(null);
  const [actionValues, setActionValues] = useState<Record<string, unknown>>({});
  const [actionResult, setActionResult] = useState<{ action: ResourceAction; result: unknown } | null>(null);
  const canCreateRecords = Boolean(
    props.createPermission && hasPermission(props.createPermission),
  );
  const canEditRecords = Boolean(
    props.editPermission && hasPermission(props.editPermission),
  );

  const load = useCallback(async (term: string, filters: Record<string, unknown> = {}) => {
    setLoading(true);
    try {
      setRecords(await api.list(term.trim(), filters));
    } catch (error) {
      setFeedback({ text: error instanceof Error ? error.message : "No se pudieron cargar los registros.", tone: "error" });
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => { void load(""); }, [load]);

  useEffect(() => {
    const formFields = canCreateRecords || canEditRecords ? props.fields ?? [] : [];
    for (const field of [...formFields, ...(props.filters ?? [])]) {
      if (!field.loadOptions) continue;
      field.loadOptions()
        .then((items) => setOptions((current) => ({ ...current, [field.name]: items })))
        .catch(() => setOptions((current) => ({ ...current, [field.name]: [] })));
    }
  }, [canCreateRecords, canEditRecords, props.fields, props.filters]);

  function openCreate() {
    setEditing(null);
    const values = { ...(props.initialValues ?? {}) };
    if ((props.fields ?? []).some((field) => field.name === "entidad") && user?.institucion) {
      values.entidad = user.institucion.id;
    }
    setForm(values);
    setFormOpen(true);
  }

  function openEdit(record: ApiRecord) {
    setEditing(record);
    const values: Record<string, unknown> = { ...(props.initialValues ?? {}) };
    for (const field of props.fields ?? []) values[field.name] = record[field.name] ?? "";
    setForm(values);
    setFormOpen(true);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      let payload: Record<string, unknown> = {};
      for (const field of props.fields ?? []) {
        if (editing && field.createOnly) continue;
        let value = form[field.name];
        if (field.type === "number" && value !== "" && value !== null) value = Number(value);
        if (field.type === "select" && value !== "") {
          const candidate = (options[field.name] ?? field.options ?? []).find((item) => String(item.value) === String(value));
          if (candidate && typeof candidate.value === "number") value = candidate.value;
        }
        if (field.emptyAsNull && value === "") value = null;
        if (field.createOnly && !value) continue;
        payload[field.name] = value;
      }
      if (props.preparePayload) payload = props.preparePayload(payload, editing);
      if (editing) await api.update(editing.id, payload);
      else await api.create(payload);
      setFormOpen(false);
      setFeedback({ text: editing ? "Registro actualizado correctamente." : "Registro creado correctamente.", tone: "success" });
      await load(search, filterValues);
    } catch (error) {
      setFeedback({ text: error instanceof Error ? error.message : "No se pudo guardar el registro.", tone: "error" });
    } finally {
      setSaving(false);
    }
  }

  async function executeConfirmation() {
    if (!confirmation) return;
    setSaving(true);
    try {
      if (confirmation.kind === "delete") {
        await api.remove(confirmation.record.id);
        setFeedback({ text: "Registro eliminado correctamente.", tone: "success" });
      } else if (confirmation.action) {
        const payload = confirmation.action.payload?.(confirmation.record);
        if (payload === null) return;
        await api.action(confirmation.record.id, confirmation.action.endpoint ?? confirmation.action.key, payload ?? {});
        setFeedback({ text: `Acción «${confirmation.action.label}» completada.`, tone: "success" });
      }
      setConfirmation(null);
      await load(search, filterValues);
    } catch (error) {
      setFeedback({ text: error instanceof Error ? error.message : "No se pudo completar la acción.", tone: "error" });
    } finally {
      setSaving(false);
    }
  }

  async function runAction(record: ApiRecord, action: ResourceAction) {
    if (action.method === "GET") {
      setSaving(true);
      try {
        const endpoint = action.endpoint ?? action.key;
        const result = await apiRequest<unknown>(`${props.apiPath}${record.id}/${endpoint}/`);
        setActionResult({ action, result });
      } catch (error) {
        setFeedback({ text: error instanceof Error ? error.message : "No se pudo consultar la información.", tone: "error" });
      } finally {
        setSaving(false);
      }
      return;
    }
    if (action.formFields?.length) {
      await Promise.all(action.formFields.map(async (field) => {
        if (!field.loadOptions) return;
        try {
          const items = await field.loadOptions(record);
          setOptions((current) => ({ ...current, [field.name]: items }));
        } catch {
          setOptions((current) => ({ ...current, [field.name]: [] }));
        }
      }));
      setActionValues(Object.fromEntries(action.formFields.map((field) => [field.name, field.type === "checkbox" ? false : ""])));
      setActionForm({ record, action });
      return;
    }
    if (action.confirm) {
      setConfirmation({ kind: "action", record, action });
      return;
    }
    setSaving(true);
    try {
      const payload = action.payload?.(record);
      if (payload === null) return;
      await api.action(record.id, action.endpoint ?? action.key, payload ?? {});
      setFeedback({ text: `Acción «${action.label}» completada.`, tone: "success" });
      await load(search, filterValues);
    } catch (error) {
      setFeedback({ text: error instanceof Error ? error.message : "No se pudo completar la acción.", tone: "error" });
    } finally {
      setSaving(false);
    }
  }

  async function submitActionForm(event: FormEvent) {
    event.preventDefault();
    if (!actionForm) return;
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {};
      for (const field of actionForm.action.formFields ?? []) {
        let value = actionValues[field.name];
        if (field.type === "number" && value !== "") value = Number(value);
        if (field.type === "select" && value !== "") {
          const candidate = (options[field.name] ?? field.options ?? []).find((item) => String(item.value) === String(value));
          if (candidate && typeof candidate.value === "number") value = candidate.value;
        }
        if (field.emptyAsNull && value === "") value = null;
        payload[field.name] = value;
      }
      await api.action(actionForm.record.id, actionForm.action.endpoint ?? actionForm.action.key, payload);
      setFeedback({ text: `Acción «${actionForm.action.label}» completada.`, tone: "success" });
      setActionForm(null);
      await load(search, filterValues);
    } catch (error) {
      setFeedback({ text: error instanceof Error ? error.message : "No se pudo completar la acción.", tone: "error" });
    } finally {
      setSaving(false);
    }
  }

  const hasRowActions = Boolean(
    (props.editPermission && hasPermission(props.editPermission))
      || (props.deletePermission && hasPermission(props.deletePermission))
      || props.actions?.some(
        (action) =>
          hasPermission(action.permission)
          && (!action.allPermissions || hasAllPermissions(action.allPermissions)),
      ),
  );
  return (
    <>
      <PageHeader eyebrow={props.eyebrow} title={props.title} description={props.description} actions={
        props.createPermission && hasPermission(props.createPermission) && props.fields?.length ? (
          <button type="button" className="button button--primary" onClick={openCreate}>Nuevo registro</button>
        ) : null
      } />
      <Feedback message={feedback.text} tone={feedback.tone} onClose={() => setFeedback({ text: "", tone: "info" })} />
      {props.extraContent}
      <section className="panel">
        <div className="toolbar">
          <form className="search-form" onSubmit={(event) => { event.preventDefault(); void load(search, filterValues); }}>
            <label className="sr-only" htmlFor={`search-${props.apiPath}`}>Buscar</label>
            <input id={`search-${props.apiPath}`} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar por nombre, código o descripción" />
            <button className="button button--secondary" type="submit">Buscar</button>
          </form>
          <span className="record-count">{records.length} registro{records.length === 1 ? "" : "s"}</span>
        </div>
        {props.filters?.length ? <form className="resource-filters" onSubmit={(event) => { event.preventDefault(); void load(search, filterValues); }}>
          {props.filters.map((field) => <label key={field.name}><span>{field.label}</span>{field.type === "select" ? <select value={String(filterValues[field.name] ?? "")} onChange={(event) => setFilterValues((current) => ({ ...current, [field.name]: event.target.value }))}><option value="">Todos</option>{(options[field.name] ?? field.options ?? []).map((option) => <option key={String(option.value)} value={option.value}>{option.label}</option>)}</select> : <input type={field.type ?? "text"} value={String(filterValues[field.name] ?? "")} placeholder={field.placeholder} onChange={(event) => setFilterValues((current) => ({ ...current, [field.name]: event.target.value }))} />}</label>)}
          <div className="resource-filters__actions"><button className="button button--secondary" type="submit">Aplicar filtros</button><button className="button button--quiet" type="button" onClick={() => { setFilterValues({}); void load(search, {}); }}>Limpiar</button></div>
        </form> : null}
        {loading ? <LoadingState label="Cargando registros" /> : records.length === 0 ? <EmptyState /> : (
          <div className="table-scroll">
            <table>
              <thead><tr>{props.columns.map((column) => <th key={column.key}>{column.label}</th>)}{hasRowActions ? <th>Acciones</th> : null}</tr></thead>
              <tbody>{records.map((record) => (
                <tr key={record.id}>
                  {props.columns.map((column) => <td key={column.key}>{column.render ? column.render(record) : displayValue(getPath(record, column.key))}</td>)}
                  {hasRowActions ? <td><div className="row-actions">
                    {props.editPermission && hasPermission(props.editPermission) && (props.canEdit?.(record) ?? true) ? <button type="button" className="link-button" onClick={() => openEdit(record)}>Editar</button> : null}
                    {(props.actions ?? []).filter((action) => hasPermission(action.permission) && (!action.allPermissions || hasAllPermissions(action.allPermissions)) && (!action.states || action.states.includes(String(record[action.stateField ?? "estado"]))) && (action.canRun?.(record) ?? true)).map((action) => (
                      <button type="button" className={`link-button${action.tone === "danger" ? " link-button--danger" : action.tone === "success" ? " link-button--success" : ""}`} key={action.key} onClick={() => void runAction(record, action)} disabled={saving}>{action.label}</button>
                    ))}
                    {props.deletePermission && hasPermission(props.deletePermission) && (props.canDelete?.(record) ?? true) ? <button type="button" className="link-button link-button--danger" onClick={() => setConfirmation({ kind: "delete", record })}>Eliminar</button> : null}
                  </div></td> : null}
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>

      <Modal open={formOpen} onClose={() => setFormOpen(false)} title={editing ? `Editar ${props.title.toLowerCase()}` : `Nuevo registro en ${props.title.toLowerCase()}`}>
        <form className="resource-form" onSubmit={submit}>
          {(props.fields ?? []).filter((field) => !(editing && field.createOnly)).map((field) => (
            field.type === "checkbox" ? (
              <label className="checkbox-field" key={field.name}><input type="checkbox" checked={Boolean(form[field.name])} disabled={Boolean(editing && field.readOnlyOnEdit)} onChange={(event) => setForm((current) => ({ ...current, [field.name]: event.target.checked }))} /><span>{field.label}</span></label>
            ) : (
              <label key={field.name}><span>{field.label}{field.required ? " *" : ""}</span>
                {field.type === "textarea" ? <textarea required={field.required} disabled={Boolean(editing && field.readOnlyOnEdit)} value={String(form[field.name] ?? "")} placeholder={field.placeholder} onChange={(event) => setForm((current) => ({ ...current, [field.name]: event.target.value }))} /> : field.type === "select" ? (
                  <select required={field.required} disabled={Boolean(editing && field.readOnlyOnEdit)} value={String(form[field.name] ?? "")} onChange={(event) => setForm((current) => ({ ...current, [field.name]: event.target.value }))}>
                    <option value="">Seleccione</option>
                    {(options[field.name] ?? field.options ?? (field.name === "entidad" && user?.institucion ? [{ value: user.institucion.id, label: `${user.institucion.codigo_oficial} · ${user.institucion.nombre}` }] : [])).map((option) => <option disabled={option.disabled} key={String(option.value)} value={option.value}>{option.label}</option>)}
                  </select>
                ) : <input type={field.type ?? "text"} required={field.required} disabled={Boolean(editing && field.readOnlyOnEdit)} min={field.min} max={field.max} step={field.step} value={String(form[field.name] ?? "")} placeholder={field.placeholder} autoComplete={field.type === "password" ? "new-password" : undefined} onChange={(event) => setForm((current) => ({ ...current, [field.name]: event.target.value }))} />}
              </label>
            )
          ))}
          <p className="form-hint">Los campos marcados con * son obligatorios.</p>
          <div className="form-actions"><button type="button" className="button button--secondary" onClick={() => setFormOpen(false)}>Cancelar</button><button type="submit" className="button button--primary" disabled={saving}>{saving ? "Guardando…" : "Guardar"}</button></div>
        </form>
      </Modal>

      <ConfirmDialog open={Boolean(confirmation)} title={confirmation?.kind === "delete" ? "Confirmar eliminación" : "Confirmar acción"} detail={confirmation?.kind === "delete" ? (props.deleteWarning?.(confirmation.record) ?? "Esta operación puede afectar relaciones existentes y no se puede deshacer.") : (confirmation?.action?.confirm ?? "Confirme que desea continuar.")} confirmLabel={confirmation?.kind === "delete" ? "Eliminar" : "Continuar"} busy={saving} onCancel={() => setConfirmation(null)} onConfirm={() => void executeConfirmation()} />
      <Modal open={Boolean(actionForm)} onClose={() => setActionForm(null)} title={actionForm?.action.label ?? "Completar acción"}>
        <form className="resource-form" onSubmit={submitActionForm}>
          {(actionForm?.action.formFields ?? []).map((field) => field.type === "checkbox" ? <label className="checkbox-field" key={field.name}><input type="checkbox" checked={Boolean(actionValues[field.name])} onChange={(event) => setActionValues((current) => ({ ...current, [field.name]: event.target.checked }))} /><span>{field.label}</span></label> : <label key={field.name}><span>{field.label}{field.required ? " *" : ""}</span>{field.type === "textarea" ? <textarea required={field.required} value={String(actionValues[field.name] ?? "")} onChange={(event) => setActionValues((current) => ({ ...current, [field.name]: event.target.value }))} /> : field.type === "select" ? <select required={field.required} value={String(actionValues[field.name] ?? "")} onChange={(event) => setActionValues((current) => ({ ...current, [field.name]: event.target.value }))}><option value="">Seleccione</option>{(options[field.name] ?? field.options ?? []).map((option) => <option disabled={option.disabled} key={String(option.value)} value={option.value}>{option.label}</option>)}</select> : <input type={field.type ?? "text"} required={field.required} min={field.min} max={field.max} step={field.step} value={String(actionValues[field.name] ?? "")} onChange={(event) => setActionValues((current) => ({ ...current, [field.name]: event.target.value }))} />}</label>)}
          <div className="form-actions"><button type="button" className="button button--secondary" onClick={() => setActionForm(null)}>Cancelar</button><button type="submit" className="button button--primary" disabled={saving}>{saving ? "Procesando…" : "Confirmar"}</button></div>
        </form>
      </Modal>
      <Modal open={Boolean(actionResult)} onClose={() => setActionResult(null)} title={actionResult?.action.resultTitle ?? actionResult?.action.label ?? "Detalle"} wide>
        {actionResult ? (actionResult.action.renderResult ? actionResult.action.renderResult(actionResult.result) : structuredValue(actionResult.result)) : null}
      </Modal>
    </>
  );
}

export function optionsFrom(
  path: string,
  label: (item: ApiRecord) => string,
  disabled?: (item: ApiRecord) => boolean,
) {
  return async () => {
    const payload = await apiRequest<ApiRecord[] | { results: ApiRecord[] }>(path, { notify: false });
    const records = normalizeList(payload);
    return records.map((record) => ({
      value: record.id,
      label: label(record),
      disabled: disabled?.(record) ?? false,
    }));
  };
}

export function apiErrorMessage(error: unknown) {
  return error instanceof ApiError || error instanceof Error ? error.message : "Ocurrió un error inesperado.";
}
