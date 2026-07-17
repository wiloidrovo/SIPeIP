import { useAuth } from "../../auth/AuthContext";
import type { SessionUser } from "../../auth/types";
import { ResourcePage, optionsFrom } from "../../components/ResourcePage";
import type { ApiRecord } from "../../services/api";

const protectedRoleCode = "superadministrador_tecnico";

function nestedRecord(record: ApiRecord, field: string) {
  const value = record[field];
  return value && typeof value === "object"
    ? value as Record<string, unknown>
    : null;
}

function scopeIsDelegable(actorScope: string | undefined, targetScope: string) {
  if (actorScope === "TOTAL") return true;
  if (actorScope === "GLOBAL") return targetScope !== "TOTAL";
  return actorScope === targetScope;
}

function roleIsUnavailable(role: ApiRecord, user: SessionUser | null) {
  if (!user || user.es_superusuario) return false;
  if (String(role.codigo) === protectedRoleCode) return true;
  const permissions = Array.isArray(role.permisos)
    ? role.permisos.filter((value): value is string => typeof value === "string")
    : [];
  const actorPermissions = new Set(user.permisos);
  return !permissions.every((permission) => actorPermissions.has(permission))
    || !scopeIsDelegable(user.rol?.alcance, String(role.alcance ?? ""));
}

function accountIsProtected(record: ApiRecord, user: SessionUser | null) {
  if (user?.es_superusuario) return false;
  const role = nestedRecord(record, "rol_detalle");
  return record.is_staff === true || String(role?.codigo ?? "") === protectedRoleCode;
}

export function UsuariosPage() {
  const { user } = useAuth();
  const fields = [
    { name: "username", label: "Nombre de usuario", required: true },
    { name: "email", label: "Correo electrónico", type: "email" as const, required: true },
    { name: "first_name", label: "Nombres", required: true },
    { name: "last_name", label: "Apellidos", required: true },
    { name: "password", label: "Contraseña temporal", type: "password" as const, required: true, createOnly: true },
    { name: "telefono", label: "Teléfono" },
    {
      name: "rol",
      label: "Rol",
      type: "select" as const,
      required: true,
      loadOptions: optionsFrom(
        "/roles/",
        (item) => String(item.nombre),
        (item) => roleIsUnavailable(item, user),
      ),
    },
    {
      name: "entidad",
      label: "Entidad",
      type: "select" as const,
      emptyAsNull: true,
      loadOptions: optionsFrom(
        "/configuracion/entidades/",
        (item) => `${String(item.codigo_oficial)} · ${String(item.nombre)}`,
      ),
    },
    {
      name: "unidad_organizacional",
      label: "Unidad organizacional",
      type: "select" as const,
      emptyAsNull: true,
      loadOptions: optionsFrom(
        "/configuracion/unidades/",
        (item) => String(item.nombre),
      ),
    },
  ];

  const canManage = (record: ApiRecord) => !accountIsProtected(record, user);
  const canChangeState = (record: ApiRecord) => (
    canManage(record) && record.id !== user?.id
  );

  return (
    <ResourcePage
      eyebrow="Administración"
      title="Usuarios"
      description="Gestione las cuentas, su institución y el rol asignado."
      apiPath="/usuarios/"
      viewPermission="usuarios.ver"
      createPermission="usuarios.crear"
      editPermission="usuarios.editar"
      deletePermission="usuarios.eliminar"
      fields={fields}
      columns={[
        { key: "username", label: "Usuario" },
        { key: "first_name", label: "Nombres", render: (item) => `${String(item.first_name)} ${String(item.last_name)}` },
        { key: "email", label: "Correo" },
        { key: "rol_detalle.nombre", label: "Rol" },
        { key: "entidad_detalle.nombre", label: "Entidad" },
        { key: "estado", label: "Estado" },
      ]}
      actions={[
        {
          key: "activar",
          label: "Activar",
          permission: "usuarios.editar",
          states: ["INACTIVO", "BLOQUEADO"],
          tone: "success",
          confirm: "El usuario podrá ingresar nuevamente al sistema.",
          canRun: canChangeState,
        },
        {
          key: "bloquear",
          label: "Bloquear",
          permission: "usuarios.editar",
          states: ["ACTIVO"],
          tone: "danger",
          confirm: "El usuario no podrá ingresar hasta que vuelva a ser activado.",
          canRun: canChangeState,
        },
      ]}
      canEdit={canManage}
      canDelete={(record) => canManage(record) && record.id !== user?.id}
      deleteWarning={(record) => `Se eliminará al usuario ${String(record.username)} si no mantiene registros relacionados.`}
    />
  );
}
