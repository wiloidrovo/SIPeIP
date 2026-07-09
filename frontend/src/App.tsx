import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import "./App.css";
import type {
  AvanceIndicador,
  Indicador,
  MetaInstitucional,
  Plan,
  Rol,
  Usuario,
} from "./services/api";
import {
  avancesIndicadoresApi,
  indicadoresApi,
  metasApi,
  planesApi,
  rolesApi,
  usuariosApi,
} from "./services/api";
import {
  validateAvanceIndicadorForm,
  validateIndicadorForm,
  validateMetaForm,
  validatePlanForm,
  validateRolForm,
  validateUsuarioForm,
} from "./utils/validation";

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
  const [planes, setPlanes] = useState<Plan[]>([]);
  const [metas, setMetas] = useState<MetaInstitucional[]>([]);
  const [indicadores, setIndicadores] = useState<Indicador[]>([]);
  const [avancesIndicadores, setAvancesIndicadores] = useState<
    AvanceIndicador[]
  >([]);
  const [mensaje, setMensaje] = useState("");
  const [cargando, setCargando] = useState(false);
  const [permisosPorRol, setPermisosPorRol] = useState<
    Record<number, string[]>
  >({});

  const [busquedaRoles, setBusquedaRoles] = useState("");
  const [busquedaUsuarios, setBusquedaUsuarios] = useState("");
  const [busquedaPlanes, setBusquedaPlanes] = useState("");
  const [busquedaMetas, setBusquedaMetas] = useState("");
  const [busquedaIndicadores, setBusquedaIndicadores] = useState("");
  const [busquedaAvances, setBusquedaAvances] = useState("");

  const [rolEditandoId, setRolEditandoId] = useState<number | null>(null);
  const [usuarioEditandoId, setUsuarioEditandoId] = useState<number | null>(
    null,
  );
  const [planEditandoId, setPlanEditandoId] = useState<number | null>(null);
  const [metaEditandoId, setMetaEditandoId] = useState<number | null>(null);
  const [indicadorEditandoId, setIndicadorEditandoId] = useState<number | null>(
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

  const [planForm, setPlanForm] = useState({
    nombre: "",
    descripcion: "",
    periodo_inicio: "",
    periodo_fin: "",
    responsable: "",
    estado: "BORRADOR" as Plan["estado"],
    activo: true,
  });

  const [metaForm, setMetaForm] = useState({
    plan: "",
    nombre: "",
    descripcion: "",
    resultado_esperado: "",
    fecha_inicio: "",
    fecha_fin: "",
    estado: "BORRADOR" as MetaInstitucional["estado"],
    activa: true,
  });

  const [indicadorForm, setIndicadorForm] = useState({
    meta: "",
    nombre: "",
    descripcion: "",
    unidad_medida: "",
    valor_base: "0.00",
    valor_meta: "",
    frecuencia: "TRIMESTRAL" as Indicador["frecuencia"],
    activo: true,
  });

  const [avanceForm, setAvanceForm] = useState({
    indicador: "",
    fecha_registro: "",
    valor: "",
    observacion: "",
    registrado_por: "",
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

  const planesFiltrados = planes.filter((plan) => {
    const texto =
      `${plan.nombre} ${plan.descripcion} ${plan.estado} ${plan.responsable_detalle?.nombre_completo || ""}`.toLowerCase();

    return texto.includes(busquedaPlanes.toLowerCase().trim());
  });

  function contarPlanesAsignadosUsuario(usuarioId: number) {
    return planes.filter((plan) => plan.responsable === usuarioId).length;
  }

  const metasFiltradas = metas.filter((meta) => {
    const texto =
      `${meta.nombre} ${meta.descripcion} ${meta.resultado_esperado} ${meta.estado} ${meta.plan_detalle.nombre}`.toLowerCase();

    return texto.includes(busquedaMetas.toLowerCase().trim());
  });

  const indicadoresFiltrados = indicadores.filter((indicador) => {
    const texto =
      `${indicador.nombre} ${indicador.descripcion} ${indicador.unidad_medida} ${indicador.frecuencia} ${indicador.meta_detalle.nombre} ${indicador.meta_detalle.plan}`.toLowerCase();

    return texto.includes(busquedaIndicadores.toLowerCase().trim());
  });

  const avancesFiltrados = avancesIndicadores.filter((avance) => {
    const texto =
      `${avance.indicador_detalle.nombre} ${avance.indicador_detalle.meta} ${avance.valor} ${avance.observacion} ${avance.registrado_por_detalle?.nombre_completo || ""}`.toLowerCase();

    return texto.includes(busquedaAvances.toLowerCase().trim());
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
      const [
        rolesData,
        usuariosData,
        planesData,
        metasData,
        indicadoresData,
        avancesData,
      ] = await Promise.all([
        rolesApi.listar(),
        usuariosApi.listar(),
        planesApi.listar(),
        metasApi.listar(),
        indicadoresApi.listar(),
        avancesIndicadoresApi.listar(),
      ]);

      setRoles(rolesData);
      setUsuarios(usuariosData);
      setPlanes(planesData);
      setMetas(metasData);
      setIndicadores(indicadoresData);
      setAvancesIndicadores(avancesData);

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

  async function crearPlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const validation = validatePlanForm(planForm);

    if (!validation.valid) {
      setMensaje(validation.message);
      return;
    }

    try {
      const payload = {
        nombre: planForm.nombre.trim(),
        descripcion: planForm.descripcion.trim(),
        periodo_inicio: planForm.periodo_inicio,
        periodo_fin: planForm.periodo_fin,
        responsable: planForm.responsable ? Number(planForm.responsable) : null,
        estado: planForm.estado,
        activo: planForm.activo,
      };

      if (planEditandoId) {
        await planesApi.actualizar(planEditandoId, payload);
        setMensaje("Plan actualizado correctamente.");
        setPlanEditandoId(null);
      } else {
        await planesApi.crear(payload);
        setMensaje("Plan creado correctamente.");
      }

      setPlanForm({
        nombre: "",
        descripcion: "",
        periodo_inicio: "",
        periodo_fin: "",
        responsable: "",
        estado: "BORRADOR",
        activo: true,
      });

      await cargarDatos(false);
    } catch (error) {
      setMensaje(
        error instanceof Error ? error.message : "No se pudo guardar el plan.",
      );
    }
  }

  function cargarPlanParaEditar(plan: Plan) {
    setPlanEditandoId(plan.id);
    setPlanForm({
      nombre: plan.nombre,
      descripcion: plan.descripcion,
      periodo_inicio: plan.periodo_inicio,
      periodo_fin: plan.periodo_fin,
      responsable: plan.responsable ? String(plan.responsable) : "",
      estado: plan.estado,
      activo: plan.activo,
    });
    setMensaje(`Editando plan ${plan.nombre}.`);
  }

  function cancelarEdicionPlan() {
    setPlanEditandoId(null);
    setPlanForm({
      nombre: "",
      descripcion: "",
      periodo_inicio: "",
      periodo_fin: "",
      responsable: "",
      estado: "BORRADOR",
      activo: true,
    });
    setMensaje("");
  }

  async function enviarPlanARevision(id: number) {
    try {
      const planActualizado = await planesApi.enviarARevision(id);
      await cargarDatos(false);
      setMensaje(`El plan ${planActualizado.nombre} fue enviado a revisión.`);
    } catch (error) {
      setMensaje(
        error instanceof Error
          ? error.message
          : "No se pudo enviar el plan a revisión.",
      );
    }
  }

  async function archivarPlan(id: number) {
    const confirmar = window.confirm("¿Desea archivar este plan?");

    if (!confirmar) {
      return;
    }

    try {
      const planActualizado = await planesApi.archivar(id);
      await cargarDatos(false);
      setMensaje(`El plan ${planActualizado.nombre} fue archivado.`);
    } catch (error) {
      setMensaje(
        error instanceof Error ? error.message : "No se pudo archivar el plan.",
      );
    }
  }

  async function eliminarPlan(id: number) {
    const confirmar = window.confirm("¿Desea eliminar este plan?");

    if (!confirmar) {
      return;
    }

    try {
      await planesApi.eliminar(id);
      await cargarDatos(false);
      setMensaje("Plan eliminado correctamente.");
    } catch (error) {
      setMensaje(
        error instanceof Error ? error.message : "No se pudo eliminar el plan.",
      );
    }
  }

  async function crearMeta(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const validation = validateMetaForm(metaForm);

    if (!validation.valid) {
      setMensaje(validation.message);
      return;
    }

    try {
      const payload = {
        plan: Number(metaForm.plan),
        nombre: metaForm.nombre.trim(),
        descripcion: metaForm.descripcion.trim(),
        resultado_esperado: metaForm.resultado_esperado.trim(),
        fecha_inicio: metaForm.fecha_inicio,
        fecha_fin: metaForm.fecha_fin,
        estado: metaForm.estado,
        activa: metaForm.activa,
      };

      if (metaEditandoId) {
        await metasApi.actualizar(metaEditandoId, payload);
        setMensaje("Meta actualizada correctamente.");
        setMetaEditandoId(null);
      } else {
        await metasApi.crear(payload);
        setMensaje("Meta creada correctamente.");
      }

      setMetaForm({
        plan: "",
        nombre: "",
        descripcion: "",
        resultado_esperado: "",
        fecha_inicio: "",
        fecha_fin: "",
        estado: "BORRADOR",
        activa: true,
      });

      await cargarDatos(false);
    } catch (error) {
      setMensaje(
        error instanceof Error ? error.message : "No se pudo guardar la meta.",
      );
    }
  }

  function cargarMetaParaEditar(meta: MetaInstitucional) {
    setMetaEditandoId(meta.id);
    setMetaForm({
      plan: String(meta.plan),
      nombre: meta.nombre,
      descripcion: meta.descripcion,
      resultado_esperado: meta.resultado_esperado,
      fecha_inicio: meta.fecha_inicio,
      fecha_fin: meta.fecha_fin,
      estado: meta.estado,
      activa: meta.activa,
    });
    setMensaje(`Editando meta ${meta.nombre}.`);
  }

  function cancelarEdicionMeta() {
    setMetaEditandoId(null);
    setMetaForm({
      plan: "",
      nombre: "",
      descripcion: "",
      resultado_esperado: "",
      fecha_inicio: "",
      fecha_fin: "",
      estado: "BORRADOR",
      activa: true,
    });
    setMensaje("");
  }

  async function archivarMeta(id: number) {
    const confirmar = window.confirm("¿Desea archivar esta meta?");

    if (!confirmar) {
      return;
    }

    try {
      const metaActualizada = await metasApi.archivar(id);
      await cargarDatos(false);
      setMensaje(`La meta ${metaActualizada.nombre} fue archivada.`);
    } catch (error) {
      setMensaje(
        error instanceof Error ? error.message : "No se pudo archivar la meta.",
      );
    }
  }

  async function eliminarMeta(id: number) {
    const confirmar = window.confirm("¿Desea eliminar esta meta?");

    if (!confirmar) {
      return;
    }

    try {
      await metasApi.eliminar(id);
      await cargarDatos(false);
      setMensaje("Meta eliminada correctamente.");
    } catch (error) {
      setMensaje(
        error instanceof Error ? error.message : "No se pudo eliminar la meta.",
      );
    }
  }

  async function crearIndicador(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const validation = validateIndicadorForm(indicadorForm);

    if (!validation.valid) {
      setMensaje(validation.message);
      return;
    }

    try {
      const payload = {
        meta: Number(indicadorForm.meta),
        nombre: indicadorForm.nombre.trim(),
        descripcion: indicadorForm.descripcion.trim(),
        unidad_medida: indicadorForm.unidad_medida.trim(),
        valor_base: Number(indicadorForm.valor_base).toFixed(2),
        valor_meta: Number(indicadorForm.valor_meta).toFixed(2),
        frecuencia: indicadorForm.frecuencia,
        activo: indicadorForm.activo,
      };

      if (indicadorEditandoId) {
        await indicadoresApi.actualizar(indicadorEditandoId, payload);
        setMensaje("Indicador actualizado correctamente.");
        setIndicadorEditandoId(null);
      } else {
        await indicadoresApi.crear(payload);
        setMensaje("Indicador creado correctamente.");
      }

      setIndicadorForm({
        meta: "",
        nombre: "",
        descripcion: "",
        unidad_medida: "",
        valor_base: "0.00",
        valor_meta: "",
        frecuencia: "TRIMESTRAL",
        activo: true,
      });

      await cargarDatos(false);
    } catch (error) {
      setMensaje(
        error instanceof Error
          ? error.message
          : "No se pudo guardar el indicador.",
      );
    }
  }

  function cargarIndicadorParaEditar(indicador: Indicador) {
    setIndicadorEditandoId(indicador.id);
    setIndicadorForm({
      meta: String(indicador.meta),
      nombre: indicador.nombre,
      descripcion: indicador.descripcion,
      unidad_medida: indicador.unidad_medida,
      valor_base: indicador.valor_base,
      valor_meta: indicador.valor_meta,
      frecuencia: indicador.frecuencia,
      activo: indicador.activo,
    });
    setMensaje(`Editando indicador ${indicador.nombre}.`);
  }

  function cancelarEdicionIndicador() {
    setIndicadorEditandoId(null);
    setIndicadorForm({
      meta: "",
      nombre: "",
      descripcion: "",
      unidad_medida: "",
      valor_base: "0.00",
      valor_meta: "",
      frecuencia: "TRIMESTRAL",
      activo: true,
    });
    setMensaje("");
  }

  async function activarIndicador(id: number) {
    try {
      await indicadoresApi.activar(id);
      await cargarDatos(false);
      setMensaje("Indicador activado correctamente.");
    } catch (error) {
      setMensaje(
        error instanceof Error
          ? error.message
          : "No se pudo activar el indicador.",
      );
    }
  }

  async function desactivarIndicador(id: number) {
    try {
      await indicadoresApi.desactivar(id);
      await cargarDatos(false);
      setMensaje("Indicador desactivado correctamente.");
    } catch (error) {
      setMensaje(
        error instanceof Error
          ? error.message
          : "No se pudo desactivar el indicador.",
      );
    }
  }

  async function eliminarIndicador(id: number) {
    const confirmar = window.confirm("¿Desea eliminar este indicador?");

    if (!confirmar) {
      return;
    }

    try {
      await indicadoresApi.eliminar(id);
      await cargarDatos(false);
      setMensaje("Indicador eliminado correctamente.");
    } catch (error) {
      setMensaje(
        error instanceof Error
          ? error.message
          : "No se pudo eliminar el indicador.",
      );
    }
  }

  async function registrarAvanceIndicador(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const validation = validateAvanceIndicadorForm(avanceForm);

    if (!validation.valid) {
      setMensaje(validation.message);
      return;
    }

    try {
      const avanceRegistrado = await indicadoresApi.registrarAvance(
        Number(avanceForm.indicador),
        {
          fecha_registro: avanceForm.fecha_registro,
          valor: Number(avanceForm.valor).toFixed(2),
          observacion: avanceForm.observacion.trim(),
          registrado_por: avanceForm.registrado_por
            ? Number(avanceForm.registrado_por)
            : null,
        },
      );

      setAvanceForm({
        indicador: "",
        fecha_registro: "",
        valor: "",
        observacion: "",
        registrado_por: "",
      });

      await cargarDatos(false);
      setMensaje(
        `Avance registrado para el indicador ${avanceRegistrado.indicador_detalle.nombre}.`,
      );
    } catch (error) {
      setMensaje(
        error instanceof Error
          ? error.message
          : "No se pudo registrar el avance del indicador.",
      );
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
        <h2>{planEditandoId ? "Editar plan" : "Registrar plan"}</h2>

        <form onSubmit={crearPlan}>
          <label>
            Nombre
            <input
              value={planForm.nombre}
              onChange={(event) =>
                setPlanForm({ ...planForm, nombre: event.target.value })
              }
              placeholder="Ej. Plan Operativo Institucional 2026"
            />
          </label>

          <label>
            Descripción
            <textarea
              value={planForm.descripcion}
              onChange={(event) =>
                setPlanForm({ ...planForm, descripcion: event.target.value })
              }
              placeholder="Descripción general del plan"
            />
          </label>

          <label>
            Fecha de inicio
            <input
              type="date"
              value={planForm.periodo_inicio}
              onChange={(event) =>
                setPlanForm({
                  ...planForm,
                  periodo_inicio: event.target.value,
                })
              }
            />
          </label>

          <label>
            Fecha de finalización
            <input
              type="date"
              value={planForm.periodo_fin}
              onChange={(event) =>
                setPlanForm({
                  ...planForm,
                  periodo_fin: event.target.value,
                })
              }
            />
          </label>

          <label>
            Responsable
            <select
              value={planForm.responsable}
              onChange={(event) =>
                setPlanForm({ ...planForm, responsable: event.target.value })
              }
            >
              <option value="">Sin responsable</option>
              {usuarios
                .filter((usuario) => usuario.is_active)
                .map((usuario) => (
                  <option key={usuario.id} value={usuario.id}>
                    {usuario.first_name || usuario.last_name
                      ? `${usuario.first_name} ${usuario.last_name}`.trim()
                      : usuario.username}
                  </option>
                ))}
            </select>
          </label>

          <label>
            Estado
            <select
              value={planForm.estado}
              onChange={(event) =>
                setPlanForm({
                  ...planForm,
                  estado: event.target.value as Plan["estado"],
                })
              }
            >
              <option value="BORRADOR">Borrador</option>
              <option value="EN_REVISION">En revisión</option>
              <option value="APROBADO">Aprobado</option>
              <option value="RECHAZADO">Rechazado</option>
              <option value="ARCHIVADO">Archivado</option>
            </select>
          </label>

          <label className="checkbox">
            <input
              type="checkbox"
              checked={planForm.activo}
              onChange={(event) =>
                setPlanForm({ ...planForm, activo: event.target.checked })
              }
            />
            Plan activo
          </label>

          <button type="submit">
            {planEditandoId ? "Actualizar plan" : "Guardar plan"}
          </button>

          {planEditandoId && (
            <button
              type="button"
              className="secondary"
              onClick={cancelarEdicionPlan}
            >
              Cancelar edición
            </button>
          )}
        </form>
      </section>

      <section className="grid">
        <div className="card">
          <h2>{metaEditandoId ? "Editar meta" : "Registrar meta"}</h2>

          <form onSubmit={crearMeta}>
            <label>
              Plan
              <select
                value={metaForm.plan}
                onChange={(event) =>
                  setMetaForm({ ...metaForm, plan: event.target.value })
                }
              >
                <option value="">Seleccione un plan</option>
                {planes
                  .filter((plan) => plan.activo && plan.estado !== "ARCHIVADO")
                  .map((plan) => (
                    <option key={plan.id} value={plan.id}>
                      {plan.nombre}
                    </option>
                  ))}
              </select>
            </label>

            <label>
              Nombre
              <input
                value={metaForm.nombre}
                onChange={(event) =>
                  setMetaForm({ ...metaForm, nombre: event.target.value })
                }
                placeholder="Ej. Mejorar la gestión institucional"
              />
            </label>

            <label>
              Descripción
              <textarea
                value={metaForm.descripcion}
                onChange={(event) =>
                  setMetaForm({ ...metaForm, descripcion: event.target.value })
                }
                placeholder="Descripción de la meta"
              />
            </label>

            <label>
              Resultado esperado
              <textarea
                value={metaForm.resultado_esperado}
                onChange={(event) =>
                  setMetaForm({
                    ...metaForm,
                    resultado_esperado: event.target.value,
                  })
                }
                placeholder="Resultado esperado al finalizar el periodo"
              />
            </label>

            <label>
              Fecha de inicio
              <input
                type="date"
                value={metaForm.fecha_inicio}
                onChange={(event) =>
                  setMetaForm({ ...metaForm, fecha_inicio: event.target.value })
                }
              />
            </label>

            <label>
              Fecha de finalización
              <input
                type="date"
                value={metaForm.fecha_fin}
                onChange={(event) =>
                  setMetaForm({ ...metaForm, fecha_fin: event.target.value })
                }
              />
            </label>

            <label>
              Estado
              <select
                value={metaForm.estado}
                onChange={(event) =>
                  setMetaForm({
                    ...metaForm,
                    estado: event.target.value as MetaInstitucional["estado"],
                  })
                }
              >
                <option value="BORRADOR">Borrador</option>
                <option value="ACTIVA">Activa</option>
                <option value="CERRADA">Cerrada</option>
                <option value="ARCHIVADA">Archivada</option>
              </select>
            </label>

            <label className="checkbox">
              <input
                type="checkbox"
                checked={metaForm.activa}
                onChange={(event) =>
                  setMetaForm({ ...metaForm, activa: event.target.checked })
                }
              />
              Meta activa
            </label>

            <button type="submit">
              {metaEditandoId ? "Actualizar meta" : "Guardar meta"}
            </button>

            {metaEditandoId && (
              <button
                type="button"
                className="secondary"
                onClick={cancelarEdicionMeta}
              >
                Cancelar edición
              </button>
            )}
          </form>
        </div>

        <div className="card">
          <h2>
            {indicadorEditandoId ? "Editar indicador" : "Registrar indicador"}
          </h2>

          <form onSubmit={crearIndicador}>
            <label>
              Meta
              <select
                value={indicadorForm.meta}
                onChange={(event) =>
                  setIndicadorForm({
                    ...indicadorForm,
                    meta: event.target.value,
                  })
                }
              >
                <option value="">Seleccione una meta</option>
                {metas
                  .filter((meta) => meta.activa && meta.estado !== "ARCHIVADA")
                  .map((meta) => (
                    <option key={meta.id} value={meta.id}>
                      {meta.nombre}
                    </option>
                  ))}
              </select>
            </label>

            <label>
              Nombre
              <input
                value={indicadorForm.nombre}
                onChange={(event) =>
                  setIndicadorForm({
                    ...indicadorForm,
                    nombre: event.target.value,
                  })
                }
                placeholder="Ej. Porcentaje de procesos automatizados"
              />
            </label>

            <label>
              Descripción
              <textarea
                value={indicadorForm.descripcion}
                onChange={(event) =>
                  setIndicadorForm({
                    ...indicadorForm,
                    descripcion: event.target.value,
                  })
                }
                placeholder="Descripción del indicador"
              />
            </label>

            <label>
              Unidad de medida
              <input
                value={indicadorForm.unidad_medida}
                onChange={(event) =>
                  setIndicadorForm({
                    ...indicadorForm,
                    unidad_medida: event.target.value,
                  })
                }
                placeholder="Ej. %, USD, unidades"
              />
            </label>

            <label>
              Valor base
              <input
                type="number"
                step="0.01"
                min="0"
                value={indicadorForm.valor_base}
                onChange={(event) =>
                  setIndicadorForm({
                    ...indicadorForm,
                    valor_base: event.target.value,
                  })
                }
              />
            </label>

            <label>
              Valor meta
              <input
                type="number"
                step="0.01"
                min="0"
                value={indicadorForm.valor_meta}
                onChange={(event) =>
                  setIndicadorForm({
                    ...indicadorForm,
                    valor_meta: event.target.value,
                  })
                }
              />
            </label>

            <label>
              Frecuencia
              <select
                value={indicadorForm.frecuencia}
                onChange={(event) =>
                  setIndicadorForm({
                    ...indicadorForm,
                    frecuencia: event.target.value as Indicador["frecuencia"],
                  })
                }
              >
                <option value="MENSUAL">Mensual</option>
                <option value="TRIMESTRAL">Trimestral</option>
                <option value="SEMESTRAL">Semestral</option>
                <option value="ANUAL">Anual</option>
              </select>
            </label>

            <label className="checkbox">
              <input
                type="checkbox"
                checked={indicadorForm.activo}
                onChange={(event) =>
                  setIndicadorForm({
                    ...indicadorForm,
                    activo: event.target.checked,
                  })
                }
              />
              Indicador activo
            </label>

            <button type="submit">
              {indicadorEditandoId
                ? "Actualizar indicador"
                : "Guardar indicador"}
            </button>

            {indicadorEditandoId && (
              <button
                type="button"
                className="secondary"
                onClick={cancelarEdicionIndicador}
              >
                Cancelar edición
              </button>
            )}
          </form>
        </div>
      </section>

      <section className="card">
        <h2>Registrar avance de indicador</h2>

        <form onSubmit={registrarAvanceIndicador}>
          <label>
            Indicador
            <select
              value={avanceForm.indicador}
              onChange={(event) =>
                setAvanceForm({ ...avanceForm, indicador: event.target.value })
              }
            >
              <option value="">Seleccione un indicador</option>
              {indicadores
                .filter((indicador) => indicador.activo)
                .map((indicador) => (
                  <option key={indicador.id} value={indicador.id}>
                    {indicador.nombre} - {indicador.meta_detalle.nombre}
                  </option>
                ))}
            </select>
          </label>

          <label>
            Fecha de registro
            <input
              type="date"
              value={avanceForm.fecha_registro}
              onChange={(event) =>
                setAvanceForm({
                  ...avanceForm,
                  fecha_registro: event.target.value,
                })
              }
            />
          </label>

          <label>
            Valor
            <input
              type="number"
              step="0.01"
              min="0"
              value={avanceForm.valor}
              onChange={(event) =>
                setAvanceForm({ ...avanceForm, valor: event.target.value })
              }
            />
          </label>

          <label>
            Registrado por
            <select
              value={avanceForm.registrado_por}
              onChange={(event) =>
                setAvanceForm({
                  ...avanceForm,
                  registrado_por: event.target.value,
                })
              }
            >
              <option value="">Sin usuario asignado</option>
              {usuarios
                .filter((usuario) => usuario.is_active)
                .map((usuario) => (
                  <option key={usuario.id} value={usuario.id}>
                    {usuario.first_name || usuario.last_name
                      ? `${usuario.first_name} ${usuario.last_name}`.trim()
                      : usuario.username}
                  </option>
                ))}
            </select>
          </label>

          <label>
            Observación
            <textarea
              value={avanceForm.observacion}
              onChange={(event) =>
                setAvanceForm({
                  ...avanceForm,
                  observacion: event.target.value,
                })
              }
              placeholder="Detalle del avance registrado"
            />
          </label>

          <button type="submit">Registrar avance</button>
        </form>
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
        <h2>Metas registradas</h2>

        <div className="toolbar">
          <input
            value={busquedaMetas}
            onChange={(event) => setBusquedaMetas(event.target.value)}
            placeholder="Buscar meta por nombre, plan o estado..."
          />
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Meta</th>
                <th>Plan</th>
                <th>Periodo</th>
                <th>Estado</th>
                <th>Indicadores</th>
                <th>Acciones</th>
              </tr>
            </thead>

            <tbody>
              {metasFiltradas.map((meta) => (
                <tr key={meta.id}>
                  <td>{meta.id}</td>
                  <td>
                    <strong>{meta.nombre}</strong>
                    <br />
                    <span>
                      {meta.resultado_esperado || "Sin resultado esperado"}
                    </span>
                  </td>
                  <td>{meta.plan_detalle.nombre}</td>
                  <td>
                    {meta.fecha_inicio} / {meta.fecha_fin}
                  </td>
                  <td>{meta.estado}</td>
                  <td>{meta.indicadores_count}</td>
                  <td className="actions">
                    <button
                      type="button"
                      onClick={() => cargarMetaParaEditar(meta)}
                    >
                      Editar
                    </button>

                    <button
                      type="button"
                      className="secondary"
                      disabled={meta.estado === "ARCHIVADA"}
                      onClick={() => archivarMeta(meta.id)}
                    >
                      Archivar
                    </button>

                    <button
                      type="button"
                      className="danger"
                      disabled={meta.indicadores_count > 0}
                      title={
                        meta.indicadores_count > 0
                          ? "No se puede eliminar una meta con indicadores asociados."
                          : "Eliminar meta"
                      }
                      onClick={() => eliminarMeta(meta.id)}
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}

              {metasFiltradas.length === 0 && (
                <tr>
                  <td colSpan={7}>No existen metas registradas.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2>Indicadores registrados</h2>

        <div className="toolbar">
          <input
            value={busquedaIndicadores}
            onChange={(event) => setBusquedaIndicadores(event.target.value)}
            placeholder="Buscar indicador por nombre, meta, plan o frecuencia..."
          />
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Indicador</th>
                <th>Meta</th>
                <th>Valores</th>
                <th>Frecuencia</th>
                <th>Avances</th>
                <th>Activo</th>
                <th>Acciones</th>
              </tr>
            </thead>

            <tbody>
              {indicadoresFiltrados.map((indicador) => (
                <tr key={indicador.id}>
                  <td>{indicador.id}</td>
                  <td>
                    <strong>{indicador.nombre}</strong>
                    <br />
                    <span>{indicador.unidad_medida}</span>
                  </td>
                  <td>{indicador.meta_detalle.nombre}</td>
                  <td>
                    Base: {indicador.valor_base}
                    <br />
                    Actual: {indicador.valor_actual}
                    <br />
                    Meta: {indicador.valor_meta}
                  </td>
                  <td>{indicador.frecuencia}</td>
                  <td>{indicador.avances_count}</td>
                  <td>{indicador.activo ? "Sí" : "No"}</td>
                  <td className="actions">
                    <button
                      type="button"
                      onClick={() => cargarIndicadorParaEditar(indicador)}
                    >
                      Editar
                    </button>

                    {indicador.activo ? (
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => desactivarIndicador(indicador.id)}
                      >
                        Desactivar
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => activarIndicador(indicador.id)}
                      >
                        Activar
                      </button>
                    )}

                    <button
                      type="button"
                      className="danger"
                      disabled={indicador.avances_count > 0}
                      title={
                        indicador.avances_count > 0
                          ? "No se puede eliminar un indicador con avances registrados."
                          : "Eliminar indicador"
                      }
                      onClick={() => eliminarIndicador(indicador.id)}
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}

              {indicadoresFiltrados.length === 0 && (
                <tr>
                  <td colSpan={8}>No existen indicadores registrados.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2>Avances de indicadores</h2>

        <div className="toolbar">
          <input
            value={busquedaAvances}
            onChange={(event) => setBusquedaAvances(event.target.value)}
            placeholder="Buscar avance por indicador, meta, valor u observación..."
          />
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Indicador</th>
                <th>Fecha</th>
                <th>Valor</th>
                <th>Registrado por</th>
                <th>Observación</th>
              </tr>
            </thead>

            <tbody>
              {avancesFiltrados.map((avance) => (
                <tr key={avance.id}>
                  <td>{avance.id}</td>
                  <td>
                    {avance.indicador_detalle.nombre}
                    <br />
                    <span>{avance.indicador_detalle.meta}</span>
                  </td>
                  <td>{avance.fecha_registro}</td>
                  <td>
                    {avance.valor} {avance.indicador_detalle.unidad_medida}
                  </td>
                  <td>
                    {avance.registrado_por_detalle?.nombre_completo ||
                      "Sin usuario asignado"}
                  </td>
                  <td>{avance.observacion || "Sin observación"}</td>
                </tr>
              ))}

              {avancesFiltrados.length === 0 && (
                <tr>
                  <td colSpan={6}>No existen avances registrados.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2>Planes registrados</h2>

        <div className="toolbar">
          <input
            value={busquedaPlanes}
            onChange={(event) => setBusquedaPlanes(event.target.value)}
            placeholder="Buscar plan por nombre, estado o responsable..."
          />
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Nombre</th>
                <th>Periodo</th>
                <th>Responsable</th>
                <th>Estado</th>
                <th>Activo</th>
                <th>Acciones</th>
              </tr>
            </thead>

            <tbody>
              {planesFiltrados.map((plan) => (
                <tr key={plan.id}>
                  <td>{plan.id}</td>
                  <td>
                    <strong>{plan.nombre}</strong>
                    <br />
                    <span>{plan.descripcion || "Sin descripción"}</span>
                  </td>
                  <td>
                    {plan.periodo_inicio} / {plan.periodo_fin}
                  </td>
                  <td>
                    {plan.responsable_detalle?.nombre_completo ||
                      "Sin responsable"}
                  </td>
                  <td>{plan.estado}</td>
                  <td>{plan.activo ? "Sí" : "No"}</td>
                  <td className="actions">
                    <button
                      type="button"
                      onClick={() => cargarPlanParaEditar(plan)}
                    >
                      Editar
                    </button>

                    <button
                      type="button"
                      disabled={
                        plan.estado !== "BORRADOR" &&
                        plan.estado !== "RECHAZADO"
                      }
                      onClick={() => enviarPlanARevision(plan.id)}
                    >
                      Enviar a revisión
                    </button>

                    <button
                      type="button"
                      className="secondary"
                      disabled={plan.estado === "ARCHIVADO"}
                      onClick={() => archivarPlan(plan.id)}
                    >
                      Archivar
                    </button>

                    <button
                      type="button"
                      className="danger"
                      disabled={
                        plan.estado === "EN_REVISION" ||
                        plan.estado === "APROBADO"
                      }
                      title={
                        plan.estado === "EN_REVISION" ||
                        plan.estado === "APROBADO"
                          ? "No se puede eliminar un plan en revisión o aprobado."
                          : "Eliminar plan"
                      }
                      onClick={() => eliminarPlan(plan.id)}
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}

              {planesFiltrados.length === 0 && (
                <tr>
                  <td colSpan={7}>No existen planes registrados.</td>
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
                <th>Planes</th>
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
                  <td>{contarPlanesAsignadosUsuario(usuario.id)}</td>
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
                      disabled={contarPlanesAsignadosUsuario(usuario.id) > 0}
                      title={
                        contarPlanesAsignadosUsuario(usuario.id) > 0
                          ? "No se puede eliminar un usuario asignado como responsable de planes."
                          : "Eliminar usuario"
                      }
                      onClick={() => eliminarUsuario(usuario.id)}
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}

              {usuariosFiltrados.length === 0 && (
                <tr>
                  <td colSpan={9}>No existen usuarios registrados.</td>
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
