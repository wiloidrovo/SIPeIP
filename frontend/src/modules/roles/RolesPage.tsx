import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useAuth } from "../../auth/AuthContext";
import type { SessionUser } from "../../auth/types";
import { ConfirmDialog, Modal } from "../../components/Modal";
import { PageHeader } from "../../components/PageHeader";
import { apiErrorMessage } from "../../components/ResourcePage";
import { EmptyState, Feedback, LoadingState } from "../../components/States";
import { apiRequest, normalizeList, resourceApi } from "../../services/api";
import type { ApiRecord } from "../../services/api";

type Role = ApiRecord & {
  codigo: string;
  nombre: string;
  descripcion: string;
  activo: boolean;
  permisos: string[];
  usuarios_count: number;
  alcance: string;
};

type PermissionGroup = {
  code: string;
  label: string;
  permissions: { code: string; label: string }[];
};

const api = resourceApi<Role>("/roles/");
const protectedRoleCode = "superadministrador_tecnico";

const scopeOptions = [
  { value: "TOTAL", label: "Acceso total" },
  { value: "GLOBAL", label: "Administración general" },
  { value: "REVISION_ENTIDAD", label: "Revisión institucional" },
  { value: "LECTURA_ENTIDAD", label: "Consulta institucional" },
  { value: "ENTIDAD", label: "Institución asignada" },
  { value: "PROPIO_ASIGNADO", label: "Registros propios o asignados" },
];

const permissionGroups: Record<string, string> = {
  usuarios: "Usuarios",
  roles: "Roles",
  configuracion: "Configuración institucional",
  planes: "Planes",
  metas: "Metas",
  indicadores: "Indicadores y avances",
  objetivos: "Objetivos",
  alineaciones: "PND y ODS",
  proyectos: "Proyectos",
  reportes: "Reportes",
  auditoria: "Auditoría",
};

const permissionLabels: Record<string, string> = {
  ver: "Consultar",
  crear: "Crear",
  editar: "Editar",
  eliminar: "Eliminar",
  asignar_permisos: "Administrar permisos",
  enviar_revision: "Enviar a revisión",
  revisar: "Iniciar revisión",
  devolver: "Devolver",
  aprobar: "Aprobar",
  rechazar: "Rechazar",
  archivar: "Archivar",
  registrar_avance: "Registrar avance",
  validar: "Validar",
  gestionar: "Gestionar",
  gestionar_catalogos: "Administrar catálogos",
  registrar_seguimiento: "Registrar seguimiento",
  exportar: "Exportar",
};

function scopeLabel(scope: string) {
  return scopeOptions.find((option) => option.value === scope)?.label ?? scope;
}

function scopeIsDelegable(actorScope: string | undefined, targetScope: string) {
  if (actorScope === "TOTAL") return true;
  if (actorScope === "GLOBAL") return targetScope !== "TOTAL";
  return actorScope === targetScope;
}

function isProtectedRole(role: Role, catalog: string[]) {
  return role.codigo === protectedRoleCode
    || (catalog.length > 0 && catalog.every((permission) => role.permisos.includes(permission)));
}

function canModifyRole(role: Role, user: SessionUser | null, catalog: string[]) {
  if (!user) return false;
  if (user.es_superusuario) return true;
  return !isProtectedRole(role, catalog)
    && scopeIsDelegable(user.rol?.alcance, role.alcance);
}

function canAssignRolePermissions(role: Role, user: SessionUser | null, catalog: string[]) {
  if (!canModifyRole(role, user, catalog)) return false;
  if (!user || user.es_superusuario) return true;
  if (role.id === user.rol?.id) return false;
  const actorPermissions = new Set(user.permisos);
  return role.permisos.every((permission) => actorPermissions.has(permission));
}

function canConfigureScope(role: Role, user: SessionUser | null, catalog: string[]) {
  if (!canModifyRole(role, user, catalog) || !user) return false;
  if (user.es_superusuario) return true;
  return role.id !== user.rol?.id
    && ["TOTAL", "GLOBAL"].includes(user.rol?.alcance ?? "");
}

function groupCatalog(catalog: string[]): PermissionGroup[] {
  const groups = new Map<string, PermissionGroup>();
  for (const permission of catalog) {
    const separator = permission.indexOf(".");
    const module = separator >= 0 ? permission.slice(0, separator) : permission;
    const action = separator >= 0 ? permission.slice(separator + 1) : "";
    const group = groups.get(module) ?? {
      code: module,
      label: permissionGroups[module] ?? module,
      permissions: [],
    };
    group.permissions.push({
      code: permission,
      label: permissionLabels[action] ?? action.replaceAll("_", " "),
    });
    groups.set(module, group);
  }
  return Array.from(groups.values());
}

export function RolesPage() {
  const { hasPermission, user } = useAuth();
  const [roles, setRoles] = useState<Role[]>([]);
  const [catalog, setCatalog] = useState<string[]>([]);
  const [selected, setSelected] = useState<Role | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [form, setForm] = useState({
    nombre: "",
    descripcion: "",
    alcance: "ENTIDAD",
  });
  const [checked, setChecked] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{
    text: string;
    tone: "success" | "error";
  }>({ text: "", tone: "success" });
  const [remove, setRemove] = useState<Role | null>(null);
  const groupedCatalog = useMemo(() => groupCatalog(catalog), [catalog]);

  const resetForm = useCallback(() => {
    setForm({ nombre: "", descripcion: "", alcance: "ENTIDAD" });
    setChecked([]);
  }, []);

  const closeEditor = useCallback(() => {
    setEditorOpen(false);
    setSelected(null);
    resetForm();
  }, [resetForm]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiRequest<Role[] | { results: Role[] }>("/roles/");
      setRoles(normalizeList(data));
      if (hasPermission("roles.asignar_permisos")) {
        const response = await apiRequest<{ permisos: string[] }>(
          "/roles/catalogo-permisos/",
        );
        setCatalog(response.permisos);
      } else {
        setCatalog([]);
      }
    } catch (cause) {
      setFeedback({ text: apiErrorMessage(cause), tone: "error" });
    } finally {
      setLoading(false);
    }
  }, [hasPermission]);

  useEffect(() => {
    void load();
  }, [load]);

  function open(role?: Role) {
    setSelected(role ?? null);
    setForm({
      nombre: role?.nombre ?? "",
      descripcion: role?.descripcion ?? "",
      alcance: role?.alcance ?? "ENTIDAD",
    });
    setChecked(role?.permisos ?? []);
    setEditorOpen(true);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (selected && !hasPermission("roles.editar")) return;
    if (!selected && !hasPermission("roles.crear")) return;
    setBusy(true);
    try {
      const roleData = { nombre: form.nombre, descripcion: form.descripcion };
      if (selected) await api.update(selected.id, roleData);
      else await api.create(roleData);
      closeEditor();
      setFeedback({ text: "El rol fue guardado correctamente.", tone: "success" });
      await load();
    } catch (cause) {
      setFeedback({ text: apiErrorMessage(cause), tone: "error" });
    } finally {
      setBusy(false);
    }
  }

  async function assign(role: Role) {
    if (!canAssignRolePermissions(role, user, catalog)) return;
    setBusy(true);
    try {
      await api.action(role.id, "asignar-permisos", { permisos: checked });
      setFeedback({ text: "Los permisos fueron actualizados.", tone: "success" });
      closeEditor();
      await load();
    } catch (cause) {
      setFeedback({ text: apiErrorMessage(cause), tone: "error" });
    } finally {
      setBusy(false);
    }
  }

  async function stateAction(role: Role, action: "activar" | "desactivar") {
    setBusy(true);
    try {
      await api.action(role.id, action);
      setFeedback({ text: "El estado del rol fue actualizado.", tone: "success" });
      await load();
    } catch (cause) {
      setFeedback({ text: apiErrorMessage(cause), tone: "error" });
    } finally {
      setBusy(false);
    }
  }

  async function configureScope(role: Role) {
    if (!canConfigureScope(role, user, catalog)) return;
    setBusy(true);
    try {
      await api.action(role.id, "configurar-alcance", { alcance: form.alcance });
      setFeedback({ text: "El alcance institucional fue actualizado.", tone: "success" });
      closeEditor();
      await load();
    } catch (cause) {
      setFeedback({ text: apiErrorMessage(cause), tone: "error" });
    } finally {
      setBusy(false);
    }
  }

  async function removeConfirmed() {
    if (!remove) return;
    setBusy(true);
    try {
      await api.remove(remove.id);
      setFeedback({ text: "El rol fue eliminado.", tone: "success" });
      setRemove(null);
      await load();
    } catch (cause) {
      setFeedback({ text: apiErrorMessage(cause), tone: "error" });
    } finally {
      setBusy(false);
    }
  }

  const selectedCanEdit = Boolean(
    selected
      && hasPermission("roles.editar")
      && canModifyRole(selected, user, catalog),
  );
  const selectedCanAssign = Boolean(
    selected
      && hasPermission("roles.asignar_permisos")
      && canAssignRolePermissions(selected, user, catalog),
  );
  const selectedCanConfigureScope = Boolean(
    selected
      && hasPermission("roles.editar")
      && canConfigureScope(selected, user, catalog),
  );

  return (
    <>
      <PageHeader
        eyebrow="Administración"
        title="Roles y permisos"
        description="Defina las responsabilidades y el alcance institucional de cada perfil."
        actions={hasPermission("roles.crear") ? (
          <button type="button" className="button button--primary" onClick={() => open()}>
            Nuevo rol
          </button>
        ) : null}
      />
      <Feedback
        message={feedback.text}
        tone={feedback.tone}
        onClose={() => setFeedback({ text: "", tone: "success" })}
      />
      <section className="panel">
        {loading ? (
          <LoadingState label="Cargando roles" />
        ) : !roles.length ? (
          <EmptyState title="No hay roles disponibles" />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Rol</th>
                  <th>Alcance</th>
                  <th>Usuarios</th>
                  <th>Estado</th>
                  <th>Permisos</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {roles.map((role) => {
                  const manageable = canModifyRole(role, user, catalog);
                  const canToggle = manageable && role.id !== user?.rol?.id;
                  return (
                    <tr key={role.id}>
                      <td>
                        <strong>{role.nombre}</strong>
                        <small className="table-detail">{role.descripcion}</small>
                      </td>
                      <td>{scopeLabel(role.alcance)}</td>
                      <td>{role.usuarios_count}</td>
                      <td>
                        <span className={`status-badge status-badge--${role.activo ? "success" : "danger"}`}>
                          {role.activo ? "ACTIVO" : "INACTIVO"}
                        </span>
                      </td>
                      <td>{role.permisos.length}</td>
                      <td>
                        <div className="row-actions">
                          {hasPermission("roles.editar") && manageable ? (
                            <button type="button" className="link-button" onClick={() => open(role)}>
                              Editar
                            </button>
                          ) : null}
                          {hasPermission("roles.asignar_permisos")
                            && canAssignRolePermissions(role, user, catalog) ? (
                              <button type="button" className="link-button" onClick={() => open(role)}>
                                Permisos
                              </button>
                            ) : null}
                          {role.activo && hasPermission("roles.editar") && canToggle ? (
                            <button type="button" className="link-button link-button--danger" onClick={() => void stateAction(role, "desactivar")}>
                              Desactivar
                            </button>
                          ) : null}
                          {!role.activo && hasPermission("roles.editar") && canToggle ? (
                            <button type="button" className="link-button link-button--success" onClick={() => void stateAction(role, "activar")}>
                              Activar
                            </button>
                          ) : null}
                          {hasPermission("roles.eliminar") && manageable && role.usuarios_count === 0 ? (
                            <button type="button" className="link-button link-button--danger" onClick={() => setRemove(role)}>
                              Eliminar
                            </button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <Modal
        open={editorOpen}
        title={selected ? `Gestionar ${selected.nombre}` : "Nuevo rol"}
        onClose={closeEditor}
        wide={selectedCanAssign}
      >
        {(!selected && hasPermission("roles.crear")) || selectedCanEdit ? (
          <form className="resource-form" onSubmit={save}>
            <label>
              <span>Nombre *</span>
              <input
                required
                value={form.nombre}
                onChange={(event) => setForm((current) => ({ ...current, nombre: event.target.value }))}
              />
            </label>
            <label>
              <span>Descripción</span>
              <textarea
                value={form.descripcion}
                onChange={(event) => setForm((current) => ({ ...current, descripcion: event.target.value }))}
              />
            </label>
            <div className="form-actions">
              <button className="button button--primary" disabled={busy}>
                Guardar datos
              </button>
            </div>
          </form>
        ) : null}

        {selected && selectedCanAssign ? (
          <section className="permissions-editor">
            <div>
              <h3>Permisos del rol</h3>
              <p>Seleccione únicamente las funciones que correspondan a este perfil.</p>
            </div>
            {groupedCatalog.length ? (
              <div className="permission-groups">
                {groupedCatalog.map((group) => (
                  <section className="permission-group" key={group.code}>
                    <h4>{group.label}</h4>
                    <div className="permission-grid">
                      {group.permissions.map((permission) => {
                        const actorCanDelegate = Boolean(
                          user?.es_superusuario || user?.permisos.includes(permission.code),
                        );
                        return (
                          <label className="permission-check" key={permission.code}>
                            <input
                              type="checkbox"
                              checked={checked.includes(permission.code)}
                              disabled={!actorCanDelegate}
                              onChange={() => setChecked((current) => (
                                current.includes(permission.code)
                                  ? current.filter((item) => item !== permission.code)
                                  : [...current, permission.code]
                              ))}
                            />
                            <span>{permission.label}</span>
                          </label>
                        );
                      })}
                    </div>
                  </section>
                ))}
              </div>
            ) : (
              <EmptyState title="No hay permisos disponibles" />
            )}
            <div className="form-actions">
              <button type="button" className="button button--primary" disabled={busy} onClick={() => void assign(selected)}>
                Guardar permisos
              </button>
            </div>
          </section>
        ) : null}

        {selected && selectedCanConfigureScope ? (
          <section className="permissions-editor">
            <div>
              <h3>Alcance institucional</h3>
              <p>Determine sobre qué registros puede trabajar este perfil.</p>
            </div>
            <div className="role-settings">
              <label>
                <span>Alcance</span>
                <select
                  value={form.alcance}
                  onChange={(event) => setForm((current) => ({ ...current, alcance: event.target.value }))}
                >
                  {scopeOptions.map((option) => (
                    <option
                      value={option.value}
                      key={option.value}
                      disabled={!user?.es_superusuario && !scopeIsDelegable(user?.rol?.alcance, option.value)}
                    >
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="form-actions">
              <button type="button" className="button button--primary" disabled={busy} onClick={() => void configureScope(selected)}>
                Guardar alcance
              </button>
            </div>
          </section>
        ) : null}
      </Modal>

      <ConfirmDialog
        open={Boolean(remove)}
        title="Eliminar rol"
        detail={`El rol ${remove?.nombre ?? ""} se eliminará si no mantiene usuarios relacionados.`}
        confirmLabel="Eliminar"
        busy={busy}
        onCancel={() => setRemove(null)}
        onConfirm={() => void removeConfirmed()}
      />
    </>
  );
}
