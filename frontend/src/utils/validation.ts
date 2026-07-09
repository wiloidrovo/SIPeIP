/**
 * Interfaz estándar para el resultado de validaciones en formularios.
 */
export type ValidationResult = {
  valid: boolean;
  message: string;
};

function ok(): ValidationResult {
  return {
    valid: true,
    message: "",
  };
}

function fail(message: string): ValidationResult {
  return {
    valid: false,
    message,
  };
}

/**
 * Valida los datos del formulario de roles.
 * Comprueba longitud, caracteres permitidos y campos obligatorios.
 */
export function validateRolForm(data: {
  nombre: string;
  descripcion: string;
}): ValidationResult {
  const nombre = data.nombre.trim();
  const descripcion = data.descripcion.trim();

  if (!nombre) {
    return fail("El nombre del rol es obligatorio.");
  }

  if (nombre.length < 3) {
    return fail("El nombre del rol debe tener al menos 3 caracteres.");
  }

  if (nombre.length > 100) {
    return fail("El nombre del rol no debe superar los 100 caracteres.");
  }

  if (!/^[A-Za-zÁÉÍÓÚáéíóúÑñ0-9\s._-]+$/.test(nombre)) {
    return fail("El nombre del rol contiene caracteres no permitidos.");
  }

  if (descripcion.length > 250) {
    return fail("La descripción del rol no debe superar los 250 caracteres.");
  }

  return ok();
}

/**
 * Valida los datos del formulario de usuarios.
 * Incluye comprobación de contraseñas seguras, formato de email y número de teléfono ecuatoriano.
 */
export function validateUsuarioForm(data: {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  password: string;
  rol: string;
  telefono: string;
}): ValidationResult {
  const username = data.username.trim();
  const email = data.email.trim();
  const firstName = data.first_name.trim();
  const lastName = data.last_name.trim();
  const password = data.password;
  const telefono = data.telefono.trim();

  if (!username) {
    return fail("El nombre de usuario es obligatorio.");
  }

  if (!/^[A-Za-z0-9._-]{3,30}$/.test(username)) {
    return fail(
      "El usuario debe tener entre 3 y 30 caracteres y solo puede usar letras, números, punto, guion o guion bajo.",
    );
  }

  if (!email) {
    return fail("El correo es obligatorio.");
  }

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return fail("Ingrese un correo válido.");
  }

  if (!firstName || firstName.length < 2) {
    return fail("Ingrese nombres válidos para el usuario.");
  }

  if (!lastName || lastName.length < 2) {
    return fail("Ingrese apellidos válidos para el usuario.");
  }

  if (!password || password.length < 8) {
    return fail("La contraseña debe tener al menos 8 caracteres.");
  }

  if (!/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
    return fail("La contraseña debe incluir al menos una letra y un número.");
  }

  if (!data.rol) {
    return fail("Debe seleccionar un rol para el usuario.");
  }

  if (telefono && !/^09\d{8}$/.test(telefono)) {
    return fail(
      "Ingrese un número celular ecuatoriano válido: debe tener 10 dígitos e iniciar con 09.",
    );
  }

  return ok();
}

export function validatePlanForm(form: {
  nombre: string;
  descripcion: string;
  periodo_inicio: string;
  periodo_fin: string;
  responsable: string;
}) {
  const nombre = form.nombre.trim();
  const descripcion = form.descripcion.trim();

  if (!nombre) {
    return fail("El nombre del plan es obligatorio.");
  }

  if (nombre.length < 3) {
    return fail("El nombre del plan debe tener al menos 3 caracteres.");
  }

  if (nombre.length > 150) {
    return fail("El nombre del plan no puede superar los 150 caracteres.");
  }

  if (descripcion.length > 1000) {
    return fail(
      "La descripción del plan no puede superar los 1000 caracteres.",
    );
  }

  if (!form.periodo_inicio) {
    return fail("La fecha de inicio del plan es obligatoria.");
  }

  if (!form.periodo_fin) {
    return fail("La fecha de finalización del plan es obligatoria.");
  }

  if (form.periodo_fin < form.periodo_inicio) {
    return fail(
      "La fecha de finalización no puede ser anterior a la fecha de inicio.",
    );
  }

  return ok();
}

export function validateMetaForm(form: {
  plan: string;
  nombre: string;
  descripcion: string;
  resultado_esperado: string;
  fecha_inicio: string;
  fecha_fin: string;
}) {
  const nombre = form.nombre.trim();
  const descripcion = form.descripcion.trim();
  const resultadoEsperado = form.resultado_esperado.trim();

  if (!form.plan) {
    return fail("Debe seleccionar un plan para la meta.");
  }

  if (!nombre) {
    return fail("El nombre de la meta es obligatorio.");
  }

  if (nombre.length < 3) {
    return fail("El nombre de la meta debe tener al menos 3 caracteres.");
  }

  if (nombre.length > 150) {
    return fail("El nombre de la meta no puede superar los 150 caracteres.");
  }

  if (descripcion.length > 1000) {
    return fail(
      "La descripción de la meta no puede superar los 1000 caracteres.",
    );
  }

  if (resultadoEsperado.length > 1000) {
    return fail("El resultado esperado no puede superar los 1000 caracteres.");
  }

  if (!form.fecha_inicio) {
    return fail("La fecha de inicio de la meta es obligatoria.");
  }

  if (!form.fecha_fin) {
    return fail("La fecha de finalización de la meta es obligatoria.");
  }

  if (form.fecha_fin < form.fecha_inicio) {
    return fail(
      "La fecha de finalización no puede ser anterior a la fecha de inicio.",
    );
  }

  return ok();
}

export function validateIndicadorForm(form: {
  meta: string;
  nombre: string;
  descripcion: string;
  unidad_medida: string;
  valor_base: string;
  valor_meta: string;
}) {
  const nombre = form.nombre.trim();
  const unidadMedida = form.unidad_medida.trim();
  const valorBase = Number(form.valor_base);
  const valorMeta = Number(form.valor_meta);

  if (!form.meta) {
    return fail("Debe seleccionar una meta para el indicador.");
  }

  if (!nombre) {
    return fail("El nombre del indicador es obligatorio.");
  }

  if (nombre.length < 3) {
    return fail("El nombre del indicador debe tener al menos 3 caracteres.");
  }

  if (nombre.length > 150) {
    return fail("El nombre del indicador no puede superar los 150 caracteres.");
  }

  if (!unidadMedida) {
    return fail("La unidad de medida es obligatoria.");
  }

  if (unidadMedida.length > 50) {
    return fail("La unidad de medida no puede superar los 50 caracteres.");
  }

  if (form.valor_base === "" || Number.isNaN(valorBase)) {
    return fail("El valor base debe ser un número válido.");
  }

  if (valorBase < 0) {
    return fail("El valor base no puede ser negativo.");
  }

  if (form.valor_meta === "" || Number.isNaN(valorMeta)) {
    return fail("El valor meta debe ser un número válido.");
  }

  if (valorMeta <= 0) {
    return fail("El valor meta debe ser mayor que cero.");
  }

  return ok();
}

export function validateAvanceIndicadorForm(form: {
  indicador: string;
  fecha_registro: string;
  valor: string;
  observacion: string;
}) {
  const valor = Number(form.valor);
  const observacion = form.observacion.trim();

  if (!form.indicador) {
    return fail("Debe seleccionar un indicador.");
  }

  if (!form.fecha_registro) {
    return fail("La fecha de registro del avance es obligatoria.");
  }

  if (form.valor === "" || Number.isNaN(valor)) {
    return fail("El valor del avance debe ser un número válido.");
  }

  if (valor < 0) {
    return fail("El valor del avance no puede ser negativo.");
  }

  if (observacion.length > 1000) {
    return fail("La observación no puede superar los 1000 caracteres.");
  }

  return ok();
}
