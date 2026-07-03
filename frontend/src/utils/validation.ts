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
