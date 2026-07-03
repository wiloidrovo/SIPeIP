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

/**
 * Componente principal de la aplicación.
 * Administra el estado global de la vista, incluyendo el listado de usuarios,
 * roles, permisos y formularios de edición/creación.
 */
function App() {
  const [roles, setRoles] = useState<Rol[]>([]);
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [mensaje, setMensaje] = useState("");
  const [cargando, setCargando] = useState(false);
  const [permisosPorRol, setPermisosPorRol] = useState<
    Record<number, string[]>
  >({});

  const [busquedaRoles, setBusquedaRoles] = useState("");
  const [busquedaUsuarios, setBusquedaUsuarios] = useState("");

  const [rolEditandoId, setRolEditandoId] = useState<number | null>(null);
  const [usuarioEditandoId, setUsuarioEditandoId] = useState<number | null>(
    null,
  );

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

  // Filtra en memoria los roles según el texto de búsqueda ingresado
  const rolesFiltrados = roles.filter((rol) => {
    const texto = `${rol.nombre} ${rol.descripcion}`.toLowerCase();
    return texto.includes(busquedaRoles.toLowerCase().trim());
  });

  // Filtra en memoria los usuarios considerando múltiples campos (nombre, correo, rol, etc.)
  const usuariosFiltrados = usuarios.filter((usuario) => {
    const texto =
      `${usuario.username} ${usuario.email} ${usuario.first_name} ${usuario.last_name} ${usuario.estado} ${usuario.rol_detalle?.nombre || ""}`.toLowerCase();
    return texto.includes(busquedaUsuarios.toLowerCase().trim());
  });

  /**
   * Obtiene la lista actualizada de roles y usuarios desde la API.
   * Inicializa el estado local de permisos por rol para la vista de checkboxes.
   */
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

  /**
   * Procesa el formulario de roles. Si hay un ID en edición, actualiza el rol;
   * de lo contrario, crea uno nuevo. Muestra los errores de validación si existen.
   */
  async function crearRol(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const validation = validateRolForm(rolForm);

    if (!validation.valid) {
      setMensaje(validation.message);
      return;
    }

    try {
      if (rolEditandoId) {
        await rolesApi.actualizar(rolEditandoId, {
          nombre: rolForm.nombre.trim(),
          descripcion: rolForm.descripcion.trim(),
          activo: rolForm.activo,
        });

        setMensaje("Rol actualizado correctamente.");
        setRolEditandoId(null);
      } else {
        await rolesApi.crear({
          nombre: rolForm.nombre.trim(),
          descripcion: rolForm.descripcion.trim(),
          activo: rolForm.activo,
        });

        setMensaje("Rol creado correctamente.");
      }

      setRolForm({
        nombre: "",
        descripcion: "",
        activo: true,
      });

      await cargarDatos(false);
    } catch (error) {
      setMensaje(
        error instanceof Error ? error.message : "No se pudo guardar el rol.",
      );
    }
  }

  function cargarRolParaEditar(rol: Rol) {
    setRolEditandoId(rol.id);
    setRolForm({
      nombre: rol.nombre,
      descripcion: rol.descripcion,
      activo: rol.activo,
    });
    setMensaje(`Editando rol ${rol.nombre}.`);
  }

  function cancelarEdicionRol() {
    setRolEditandoId(null);
    setRolForm({
      nombre: "",
      descripcion: "",
      activo: true,
    });
    setMensaje("");
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

  /**
   * Envía los permisos seleccionados actualmente en el UI hacia el backend
   * para actualizar los accesos del rol especificado.
   */
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

  /** Activa un rol, permitiendo que sus usuarios hereden sus permisos. */
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

  /** Desactiva un rol, impidiendo su uso. Fallará si tiene usuarios asignados. */
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

  /**
   * Procesa el formulario de usuarios (creación o edición).
   * En edición, la contraseña es opcional. Sincroniza la lista completa al finalizar.
   */
  async function crearUsuario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const validation = validateUsuarioForm({
      ...usuarioForm,
      password:
        usuarioEditandoId && !usuarioForm.password
          ? "Password123"
          : usuarioForm.password,
    });

    if (!validation.valid) {
      setMensaje(validation.message);
      return;
    }

    try {
      const payload = {
        username: usuarioForm.username.trim(),
        email: usuarioForm.email.trim(),
        first_name: usuarioForm.first_name.trim(),
        last_name: usuarioForm.last_name.trim(),
        telefono: usuarioForm.telefono.trim(),
        rol: Number(usuarioForm.rol),
        estado: usuarioForm.estado,
        is_active: usuarioForm.is_active,
        is_staff: usuarioForm.is_staff,
        ...(usuarioForm.password ? { password: usuarioForm.password } : {}),
      };

      if (usuarioEditandoId) {
        await usuariosApi.actualizar(usuarioEditandoId, payload);
        setMensaje("Usuario actualizado correctamente.");
        setUsuarioEditandoId(null);
      } else {
        await usuariosApi.crear({
          ...payload,
          password: usuarioForm.password,
        });
        setMensaje("Usuario creado correctamente.");
      }

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

      await cargarDatos(false);
    } catch (error) {
      setMensaje(
        error instanceof Error
          ? error.message
          : "No se pudo guardar el usuario.",
      );
    }
  }

  function cargarUsuarioParaEditar(usuario: Usuario) {
    setUsuarioEditandoId(usuario.id);
    setUsuarioForm({
      username: usuario.username,
      email: usuario.email,
      first_name: usuario.first_name,
      last_name: usuario.last_name,
      password: "",
      rol: usuario.rol ? String(usuario.rol) : "",
      estado: usuario.estado,
      telefono: usuario.telefono,
      is_active: usuario.is_active,
      is_staff: usuario.is_staff,
    });
    setMensaje(`Editando usuario ${usuario.username}.`);
  }

  function cancelarEdicionUsuario() {
    setUsuarioEditandoId(null);
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
    setMensaje("");
  }

  /** Restaura el acceso de un usuario al sistema. */
  async function activarUsuario(id: number) {
    try {
      await usuariosApi.activar(id);
      setMensaje("Usuario activado correctamente.");
      await cargarDatos();
    } catch (error) {
      setMensaje(error instanceof Error ? error.message : "Ocurrió un error.");
    }
  }

  /** Suspende el acceso de un usuario indefinidamente. */
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

            <button type="submit">
              {rolEditandoId ? "Actualizar rol" : "Guardar rol"}
            </button>

            {rolEditandoId && (
              <button
                type="button"
                className="secondary"
                onClick={cancelarEdicionRol}
              >
                Cancelar edición
              </button>
            )}
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
                {roles
                  .filter(
                    (rol) => rol.activo || String(rol.id) === usuarioForm.rol,
                  )
                  .map((rol) => (
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

            <button type="submit">
              {usuarioEditandoId ? "Actualizar usuario" : "Guardar usuario"}
            </button>

            {usuarioEditandoId && (
              <button
                type="button"
                className="secondary"
                onClick={cancelarEdicionUsuario}
              >
                Cancelar edición
              </button>
            )}
          </form>
        </div>
      </section>

      <section className="card">
        <h2>Roles registrados</h2>

        <div className="toolbar">
          <input
            value={busquedaRoles}
            onChange={(event) => setBusquedaRoles(event.target.value)}
            placeholder="Buscar rol por nombre o descripción..."
          />
        </div>

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
              {rolesFiltrados.map((rol) => (
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
                      onClick={() => cargarRolParaEditar(rol)}
                    >
                      Editar
                    </button>

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

              {rolesFiltrados.length === 0 && (
                <tr>
                  <td colSpan={7}>No existen roles registrados.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2>Usuarios registrados</h2>

        <div className="toolbar">
          <input
            value={busquedaUsuarios}
            onChange={(event) => setBusquedaUsuarios(event.target.value)}
            placeholder="Buscar usuario por nombre, correo, rol o estado..."
          />
        </div>

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
              {usuariosFiltrados.map((usuario) => (
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
                      onClick={() => cargarUsuarioParaEditar(usuario)}
                    >
                      Editar
                    </button>
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

              {usuariosFiltrados.length === 0 && (
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
