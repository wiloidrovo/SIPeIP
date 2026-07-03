import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import "./App.css";
import type { Rol, Usuario } from "./services/api";
import { rolesApi, usuariosApi } from "./services/api";
import { validateRolForm, validateUsuarioForm } from "./utils/validation";

const permisosBase = [
  "usuarios.ver",
  "usuarios.crear",
  "usuarios.editar",
  "usuarios.eliminar",
  "roles.ver",
  "roles.crear",
  "roles.editar",
  "roles.eliminar",
  "roles.asignar_permisos",
];

function App() {
  const [roles, setRoles] = useState<Rol[]>([]);
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [mensaje, setMensaje] = useState("");
  const [cargando, setCargando] = useState(false);
  const [permisosPorRol, setPermisosPorRol] = useState<
    Record<number, string[]>
  >({});

  const [rolForm, setRolForm] = useState({
    nombre: "",
    descripcion: "",
    activo: true,
  });

  const [usuarioForm, setUsuarioForm] = useState({
    username: "",
    email: "",
    first_name: "",
    last_name: "",
    password: "",
    rol: "",
    estado: "ACTIVO" as Usuario["estado"],
    telefono: "",
    is_active: true,
    is_staff: false,
  });

  async function cargarDatos(limpiarMensaje = true) {
    setCargando(true);

    if (limpiarMensaje) {
      setMensaje("");
    }

    try {
      const [rolesData, usuariosData] = await Promise.all([
        rolesApi.listar(),
        usuariosApi.listar(),
      ]);

      setRoles(rolesData);
      setUsuarios(usuariosData);

      const permisosIniciales = rolesData.reduce<Record<number, string[]>>(
        (acumulador, rol) => {
          acumulador[rol.id] = rol.permisos || [];
          return acumulador;
        },
        {},
      );

      setPermisosPorRol(permisosIniciales);
    } catch (error) {
      setMensaje("No se pudieron cargar los datos desde el backend.");
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    cargarDatos();
  }, []);

  async function crearRol(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const validation = validateRolForm(rolForm);

    if (!validation.valid) {
      setMensaje(validation.message);
      return;
    }

    try {
      await rolesApi.crear({
        nombre: rolForm.nombre.trim(),
        descripcion: rolForm.descripcion.trim(),
        activo: rolForm.activo,
      });

      setRolForm({
        nombre: "",
        descripcion: "",
        activo: true,
      });

      setMensaje("Rol creado correctamente.");
      await cargarDatos();
    } catch (error) {
      setMensaje(
        error instanceof Error ? error.message : "No se pudo crear el rol.",
      );
    }
  }

  function alternarPermiso(rolId: number, permiso: string) {
    setPermisosPorRol((estadoActual) => {
      const permisosActuales = estadoActual[rolId] || [];

      const permisosActualizados = permisosActuales.includes(permiso)
        ? permisosActuales.filter((permisoActual) => permisoActual !== permiso)
        : [...permisosActuales, permiso];

      return {
        ...estadoActual,
        [rolId]: permisosActualizados,
      };
    });
  }

  async function asignarPermisos(id: number) {
    const permisosSeleccionados = permisosPorRol[id] || [];

    try {
      const rolActualizado = await rolesApi.asignarPermisos(
        id,
        permisosSeleccionados,
      );

      await cargarDatos(false);

      setMensaje(
        `Permisos actualizados para el rol ${rolActualizado.nombre}. Total: ${rolActualizado.permisos.length}.`,
      );
    } catch (error) {
      setMensaje(
        error instanceof Error
          ? error.message
          : "No se pudieron asignar los permisos.",
      );
    }
  }

  async function activarRol(id: number) {
    try {
      await rolesApi.activar(id);
      setMensaje("Rol activado correctamente.");
      await cargarDatos();
    } catch (error) {
      setMensaje(
        error instanceof Error ? error.message : "No se pudo activar el rol.",
      );
    }
  }

  async function desactivarRol(id: number) {
    try {
      await rolesApi.desactivar(id);
      setMensaje("Rol desactivado correctamente.");
      await cargarDatos();
    } catch (error) {
      setMensaje(
        error instanceof Error
          ? error.message
          : "No se pudo desactivar el rol.",
      );
    }
  }

  async function eliminarRol(id: number) {
    const rol = roles.find((item) => item.id === id);

    if (rol && rol.usuarios_count > 0) {
      setMensaje(
        `No se puede eliminar el rol ${rol.nombre} porque está asignado a ${rol.usuarios_count} usuario(s). Desactive el rol o reasigne los usuarios antes de eliminarlo.`,
      );
      return;
    }

    const confirmar = window.confirm("¿Desea eliminar este rol?");

    if (!confirmar) {
      return;
    }

    try {
      await rolesApi.eliminar(id);
      await cargarDatos(false);
      setMensaje("Rol eliminado correctamente.");
    } catch (error) {
      setMensaje(
        error instanceof Error ? error.message : "No se pudo eliminar el rol.",
      );
    }
  }

  async function crearUsuario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const validation = validateUsuarioForm(usuarioForm);

    if (!validation.valid) {
      setMensaje(validation.message);
      return;
    }

    try {
      await usuariosApi.crear({
        ...usuarioForm,
        username: usuarioForm.username.trim(),
        email: usuarioForm.email.trim(),
        first_name: usuarioForm.first_name.trim(),
        last_name: usuarioForm.last_name.trim(),
        telefono: usuarioForm.telefono.trim(),
        rol: Number(usuarioForm.rol),
      });

      setUsuarioForm({
        username: "",
        email: "",
        first_name: "",
        last_name: "",
        password: "",
        rol: "",
        estado: "ACTIVO",
        telefono: "",
        is_active: true,
        is_staff: false,
      });

      setMensaje("Usuario creado correctamente.");
      await cargarDatos();
    } catch (error) {
      setMensaje(
        error instanceof Error ? error.message : "No se pudo crear el usuario.",
      );
    }
  }

  async function activarUsuario(id: number) {
    try {
      await usuariosApi.activar(id);
      setMensaje("Usuario activado correctamente.");
      await cargarDatos();
    } catch (error) {
      setMensaje(error instanceof Error ? error.message : "Ocurrió un error.");
    }
  }

  async function bloquearUsuario(id: number) {
    try {
      await usuariosApi.bloquear(id);
      setMensaje("Usuario bloqueado correctamente.");
      await cargarDatos();
    } catch (error) {
      setMensaje(error instanceof Error ? error.message : "Ocurrió un error.");
    }
  }

  async function eliminarUsuario(id: number) {
    const confirmar = window.confirm("¿Desea eliminar este usuario?");

    if (!confirmar) {
      return;
    }

    try {
      await usuariosApi.eliminar(id);
      setMensaje("Usuario eliminado correctamente.");
      await cargarDatos();
    } catch (error) {
      setMensaje(error instanceof Error ? error.message : "Ocurrió un error.");
    }
  }

  return (
    <main className="app">
      <section className="hero">
        <div>
          <p className="eyebrow">Sprint 1</p>
          <h1>SIPeIP - Gestión de usuarios y roles</h1>
          <p>
            Interfaz inicial conectada al backend Django REST Framework para
            administrar usuarios, roles, permisos y estados de acceso.
          </p>
        </div>

        <button type="button" onClick={() => cargarDatos()}>
          {cargando ? "Cargando..." : "Actualizar datos"}
        </button>
      </section>

      {mensaje && <div className="message">{mensaje}</div>}

      <section className="grid">
        <div className="card">
          <h2>Registrar rol</h2>

          <form onSubmit={crearRol}>
            <label>
              Nombre
              <input
                value={rolForm.nombre}
                onChange={(event) =>
                  setRolForm({ ...rolForm, nombre: event.target.value })
                }
                placeholder="Ej. Administrador"
              />
            </label>

            <label>
              Descripción
              <textarea
                value={rolForm.descripcion}
                onChange={(event) =>
                  setRolForm({ ...rolForm, descripcion: event.target.value })
                }
                placeholder="Descripción del rol"
              />
            </label>

            <label className="checkbox">
              <input
                type="checkbox"
                checked={rolForm.activo}
                onChange={(event) =>
                  setRolForm({ ...rolForm, activo: event.target.checked })
                }
              />
              Rol activo
            </label>

            <button type="submit">Guardar rol</button>
          </form>
        </div>

        <div className="card">
          <h2>Registrar usuario</h2>

          <form onSubmit={crearUsuario}>
            <label>
              Usuario
              <input
                value={usuarioForm.username}
                onChange={(event) =>
                  setUsuarioForm({
                    ...usuarioForm,
                    username: event.target.value,
                  })
                }
                placeholder="usuario.prueba"
              />
            </label>

            <label>
              Correo
              <input
                type="text"
                inputMode="email"
                value={usuarioForm.email}
                onChange={(event) =>
                  setUsuarioForm({ ...usuarioForm, email: event.target.value })
                }
                placeholder="usuario@sipeip.local"
              />
            </label>

            <label>
              Nombres
              <input
                value={usuarioForm.first_name}
                onChange={(event) =>
                  setUsuarioForm({
                    ...usuarioForm,
                    first_name: event.target.value,
                  })
                }
              />
            </label>

            <label>
              Apellidos
              <input
                value={usuarioForm.last_name}
                onChange={(event) =>
                  setUsuarioForm({
                    ...usuarioForm,
                    last_name: event.target.value,
                  })
                }
              />
            </label>

            <label>
              Contraseña
              <input
                type="password"
                value={usuarioForm.password}
                onChange={(event) =>
                  setUsuarioForm({
                    ...usuarioForm,
                    password: event.target.value,
                  })
                }
              />
            </label>

            <label>
              Rol
              <select
                value={usuarioForm.rol}
                onChange={(event) =>
                  setUsuarioForm({ ...usuarioForm, rol: event.target.value })
                }
              >
                <option value="">Sin rol</option>
                {roles.map((rol) => (
                  <option key={rol.id} value={rol.id}>
                    {rol.nombre}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Teléfono
              <input
                value={usuarioForm.telefono}
                onChange={(event) =>
                  setUsuarioForm({
                    ...usuarioForm,
                    telefono: event.target.value,
                  })
                }
              />
            </label>

            <button type="submit">Guardar usuario</button>
          </form>
        </div>
      </section>

      <section className="card">
        <h2>Roles registrados</h2>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Nombre</th>
                <th>Descripción</th>
                <th>Activo</th>
                <th>Permisos</th>
                <th>Usuarios</th>
                <th>Acciones</th>
              </tr>
            </thead>

            <tbody>
              {roles.map((rol) => (
                <tr key={rol.id}>
                  <td>{rol.id}</td>
                  <td>{rol.nombre}</td>
                  <td>{rol.descripcion || "Sin descripción"}</td>
                  <td>{rol.activo ? "Sí" : "No"}</td>
                  <td>
                    <div className="permissions-selector">
                      {permisosBase.map((permiso) => (
                        <label key={permiso} className="permission-option">
                          <input
                            type="checkbox"
                            checked={(permisosPorRol[rol.id] || []).includes(
                              permiso,
                            )}
                            onChange={() => alternarPermiso(rol.id, permiso)}
                          />
                          <span>{permiso}</span>
                        </label>
                      ))}
                    </div>
                  </td>
                  <td>{rol.usuarios_count}</td>
                  <td className="actions">
                    <button
                      type="button"
                      onClick={() => asignarPermisos(rol.id)}
                    >
                      Guardar permisos
                    </button>

                    {rol.activo ? (
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => desactivarRol(rol.id)}
                      >
                        Desactivar
                      </button>
                    ) : (
                      <button type="button" onClick={() => activarRol(rol.id)}>
                        Activar
                      </button>
                    )}

                    <button
                      type="button"
                      className="danger"
                      disabled={rol.usuarios_count > 0}
                      title={
                        rol.usuarios_count > 0
                          ? "No se puede eliminar un rol asignado a usuarios."
                          : "Eliminar rol"
                      }
                      onClick={() => eliminarRol(rol.id)}
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}

              {roles.length === 0 && (
                <tr>
                  <td colSpan={6}>No existen roles registrados.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2>Usuarios registrados</h2>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Usuario</th>
                <th>Nombre</th>
                <th>Correo</th>
                <th>Rol</th>
                <th>Estado</th>
                <th>Activo</th>
                <th>Acciones</th>
              </tr>
            </thead>

            <tbody>
              {usuarios.map((usuario) => (
                <tr key={usuario.id}>
                  <td>{usuario.id}</td>
                  <td>{usuario.username}</td>
                  <td>
                    {usuario.first_name} {usuario.last_name}
                  </td>
                  <td>{usuario.email || "Sin correo"}</td>
                  <td>{usuario.rol_detalle?.nombre || "Sin rol"}</td>
                  <td>{usuario.estado}</td>
                  <td>{usuario.is_active ? "Sí" : "No"}</td>
                  <td className="actions">
                    <button
                      type="button"
                      onClick={() => activarUsuario(usuario.id)}
                    >
                      Activar
                    </button>
                    <button
                      type="button"
                      onClick={() => bloquearUsuario(usuario.id)}
                    >
                      Bloquear
                    </button>
                    <button
                      type="button"
                      className="danger"
                      onClick={() => eliminarUsuario(usuario.id)}
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}

              {usuarios.length === 0 && (
                <tr>
                  <td colSpan={8}>No existen usuarios registrados.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

export default App;
