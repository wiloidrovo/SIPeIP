# SIPeIP

SIPeIP es una aplicación web para gestionar planificación, seguimiento, inversión pública, reportes y trazabilidad en la Secretaría Nacional de Planificación.

El sistema funciona como una SPA modular con autenticación de sesión, control de acceso basado en permisos, alcance institucional y rutas protegidas.

## Estado funcional

El alcance implementado incluye:

- autenticación mediante sesión Django y protección CSRF;
- RBAC centralizado con 52 permisos y denegación por defecto;
- alcance institucional aplicado en los querysets del backend;
- panel y navegación condicionados por permisos efectivos;
- gestión de usuarios, roles, entidades y unidades organizacionales;
- planes, metas, indicadores y avances;
- objetivos estratégicos y alineación PND/ODS;
- proyectos de inversión, hitos y seguimiento físico-financiero;
- auditoría de accesos y operaciones;
- reportes con vista previa y exportación a JSON, CSV, XLSX y PDF;
- interfaz responsive con rutas protegidas y módulos frontend separados.

Los cambios de estado se ejecutan mediante acciones autorizadas. No se permite alterar libremente estados ni utilizar el nombre de un rol como único control de seguridad.

## Tecnologías

### Backend

- Python 3.11
- Django 5.2.15
- Django REST Framework 3.17.1
- PostgreSQL
- `django-cors-headers`
- `psycopg`
- OpenPyXL y ReportLab para exportaciones

### Frontend

- React 18.3.1
- React Router 6
- TypeScript 5.6.3
- Vite 5.4.11
- CSS institucional sin frameworks visuales externos

## Arquitectura

```text
Navegador
   │
   ▼
React SPA (localhost:5173)
   │  sesión, cookies y CSRF
   ▼
Django REST API (localhost:8000)
   │  permisos y alcance institucional
   ▼
PostgreSQL
```

El backend es la autoridad para validaciones, permisos, alcance y transiciones de estado. Ocultar un botón en el frontend mejora la experiencia, pero no sustituye la autorización de la API.

### Seguridad

- La sesión se almacena en el servidor Django.
- La cookie de sesión es `HttpOnly` y `SameSite=Lax`.
- CSRF es obligatorio para `POST`, `PUT`, `PATCH` y `DELETE`.
- El frontend usa `credentials: "include"` y no guarda contraseñas, cookies ni secretos en `localStorage`.
- La duración predeterminada de la sesión es de 900 segundos y puede configurarse mediante el entorno.
- El inicio de sesión tiene límite de intentos.
- La API responde con `401` sin autenticación, `403` sin permiso y `409` ante conflictos de negocio o integridad.
- Los usuarios con alcance institucional solo pueden consultar registros dentro de su ámbito.

## Módulos

| Módulo        | Responsabilidad principal                                                       |
| ------------- | ------------------------------------------------------------------------------- |
| Autenticación | Login, sesión, renovación, logout e identidad actual                            |
| Dashboard     | Resumen y accesos según permisos efectivos                                      |
| Usuarios      | Creación, edición, activación, bloqueo y adscripción institucional              |
| Roles         | Catálogo de roles, permisos, alcance, activación y protección contra escalación |
| Configuración | Entidades y unidades organizacionales jerárquicas                               |
| Planes        | Flujo de borrador, revisión, devolución, aprobación, rechazo y archivo          |
| Metas         | Activación, cierre, archivo y relación con planes                               |
| Indicadores   | Medición, activación, validación y registro de avances                          |
| Objetivos     | Objetivos estratégicos institucionales                                          |
| Alineación    | Catálogos PND/ODS y matriz de alineación                                        |
| Proyectos     | Proyectos de inversión, cronograma, hitos y seguimiento                         |
| Reportes      | Vista previa y exportación con filtros autorizados                              |
| Auditoría     | Consulta de accesos, cambios y resultados de operaciones                        |

## Estructura principal

```text
SIPeIP/
├── backend/
│   ├── apps/
│   │   ├── autenticacion/
│   │   ├── auditoria/
│   │   ├── configuracion/
│   │   ├── dashboard/
│   │   ├── metas/
│   │   ├── objetivos/
│   │   ├── planes/
│   │   ├── proyectos/
│   │   ├── reportes/
│   │   ├── roles/
│   │   └── usuarios/
│   ├── config/
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── auth/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── modules/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── styles/
│   │   └── utils/
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

`frontend/src/App.tsx` se limita a componer el router y el proveedor de autenticación. La funcionalidad se encuentra distribuida por páginas, módulos, componentes y servicios.

## Requisitos locales

- Python 3.11 o superior compatible
- Node.js 18 o superior
- npm
- PostgreSQL en ejecución
- PowerShell en Windows para utilizar los comandos de los ejemplos

La base local utilizada por el inicializador debe llamarse exactamente `sipeip_db`.

## Instalación inicial

### 1. Preparar PostgreSQL

Cree una base PostgreSQL local llamada `sipeip_db` y un usuario con permisos sobre ella. Puede hacerlo mediante pgAdmin o las herramientas de línea de comandos de PostgreSQL.

No utilice el inicializador contra una base externa o de producción. El propio comando comprueba que:

- `DEBUG=True`;
- el motor sea PostgreSQL;
- el host sea local;
- la base se llame `sipeip_db`.

### 2. Configurar el backend

Desde la raíz del repositorio:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edite `backend/.env` con valores exclusivos para su entorno local:

```env
SECRET_KEY=reemplace-por-una-clave-local
DEBUG=True

DB_NAME=sipeip_db
DB_USER=sipeip_user
DB_PASSWORD=reemplace-por-la-clave-local-de-postgresql
DB_HOST=localhost
DB_PORT=5432
```

Nunca agregue `backend/.env` ni credenciales reales al repositorio.

Ejecute las migraciones:

```powershell
python manage.py migrate
```

### 3. Inicializar roles y datos locales

El comando autorizado es idempotente y crea los seis roles base, usuarios iniciales y registros institucionales de referencia:

```powershell
$claveSegura = Read-Host "Contraseña temporal" -AsSecureString
$claveTemporal = [System.Net.NetworkCredential]::new("", $claveSegura).Password
python manage.py inicializar_sistema --password $claveTemporal
Remove-Variable claveTemporal, claveSegura
```

Cada ejecución vuelve a establecer esa contraseña para los seis usuarios locales:

| Usuario              | Perfil                      |
| -------------------- | --------------------------- |
| `administrador`      | Administrador del Sistema   |
| `planificador`       | Planificador Institucional  |
| `supervisor`         | Supervisor de Planificación |
| `externo`            | Usuario Externo             |
| `auditor`            | Auditor / Control Interno   |
| `superadministrador` | Superadministrador técnico  |

La contraseña es la suministrada durante la ejecución y no está almacenada en el código. El superadministrador técnico es una cuenta excepcional y no debe utilizarse para operación cotidiana.

Los catálogos y registros creados por este comando sirven para desarrollo y validación local. No deben interpretarse como una publicación oficial de catálogos institucionales, PND u ODS.

### 4. Configurar el frontend

En una terminal independiente:

```powershell
cd frontend
npm ci
```

`npm ci` utiliza las versiones registradas en `package-lock.json`. No es necesario actualizar paquetes para iniciar el proyecto.

## Inicio cotidiano

Terminal del backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

Terminal del frontend:

```powershell
cd frontend
npm run dev
```

Abra la aplicación en:

```text
http://localhost:5173
```

Direcciones locales:

- SPA: `http://localhost:5173`
- API: `http://localhost:8000/api/`
- Administración Django: `http://localhost:8000/admin/`

Use `localhost` de forma consistente en el navegador. `python manage.py migrate` solo debe repetirse cuando existan migraciones nuevas; no es un requisito para cada arranque.

## Rutas frontend

| Ruta                       | Acceso              |
| -------------------------- | ------------------- |
| `/login`                   | Pública             |
| `/dashboard`               | Usuario autenticado |
| `/usuarios`                | `usuarios.ver`      |
| `/roles`                   | `roles.ver`         |
| `/configuracion/entidades` | `configuracion.ver` |
| `/configuracion/unidades`  | `configuracion.ver` |
| `/planes`                  | `planes.ver`        |
| `/metas`                   | `metas.ver`         |
| `/indicadores`             | `indicadores.ver`   |
| `/avances`                 | `indicadores.ver`   |
| `/objetivos`               | `objetivos.ver`     |
| `/alineacion/pnd`          | `alineaciones.ver`  |
| `/alineacion/ods`          | `alineaciones.ver`  |
| `/proyectos`               | `proyectos.ver`     |
| `/reportes`                | `reportes.ver`      |
| `/auditoria`               | `auditoria.ver`     |

Las rutas se protegen en React para navegación y en Django/DRF para seguridad efectiva.

## API

### Autenticación

```text
GET  /api/auth/csrf/
POST /api/auth/login/
POST /api/auth/refresh/
POST /api/auth/logout/
GET  /api/auth/me/
```

### Recursos principales

```text
/api/dashboard/
/api/roles/
/api/usuarios/
/api/configuracion/entidades/
/api/configuracion/unidades/
/api/planes/
/api/metas/
/api/indicadores/
/api/avances-indicadores/
/api/objetivos-estrategicos/
/api/ejes-pnd/
/api/objetivos-pnd/
/api/ods/
/api/alineaciones/
/api/tipologias-intervencion/
/api/proyectos/
/api/hitos-proyectos/
/api/seguimientos-proyectos/
/api/reportes/
/api/auditoria/eventos/
```

Las acciones específicas de revisión, aprobación, archivo, validación y seguimiento se exponen en los recursos correspondientes y requieren permiso, estado válido y alcance sobre el registro.

## Roles y alcance

| Rol base                    | Alcance general                                        |
| --------------------------- | ------------------------------------------------------ |
| Administrador del Sistema   | Administración global                                  |
| Planificador Institucional  | Registros propios o asignados dentro de su institución |
| Supervisor de Planificación | Revisión dentro de su institución                      |
| Usuario Externo             | Únicamente su institución                              |
| Auditor / Control Interno   | Lectura dentro de su institución                       |
| Superadministrador técnico  | Acceso técnico total excepcional                       |

La autorización se decide mediante códigos de permiso. Un usuario o rol inactivo no otorga permisos, y un administrador ordinario no puede delegar permisos superiores a los propios ni modificar el rol técnico protegido.

## Comprobaciones del proyecto

### Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py check
python manage.py makemigrations --check --dry-run
```

Para aplicar migraciones nuevas a la base local:

```powershell
python manage.py migrate
```

### Frontend

```powershell
cd frontend
npm run build
```

El build ejecuta el compilador TypeScript antes de generar el paquete de Vite.
