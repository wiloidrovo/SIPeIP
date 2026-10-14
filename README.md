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
- planes, metas vinculadas a objetivos estratégicos, indicadores y avances;
- expediente integral del plan con contenido, validaciones, historial y decisiones;
- revisión asignada a un supervisor y validación independiente de alineaciones e indicadores;
- seguimiento ponderado desde los indicadores hasta las metas, objetivos y planes;
- objetivos estratégicos y alineación PND/ODS con trazabilidad desde las metas;
- proyectos de inversión, hitos y seguimiento físico-financiero;
- auditoría de accesos y operaciones;
- reportes con vista previa y exportación a JSON, CSV, XLSX y PDF;
- pruebas funcionales reproducibles mediante Django y una colección Postman;
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

### Cadena de planificación y seguimiento

```text
Entidad institucional
├── Plan
│   └── Meta
│       ├── Objetivo estratégico principal
│       └── Indicador
│           └── Avances
└── Objetivo estratégico
    └── Alineación
        ├── Objetivo PND
        └── ODS
```

Cada meta contribuye a un único objetivo estratégico principal. Un objetivo puede agrupar varias metas y conectarlas con el PND y los ODS mediante la matriz de alineación. Esta estructura evita duplicar metas o avances y permite consultar la contribución institucional desde ambos módulos.

El plan y el objetivo seleccionados para una meta deben pertenecer a la misma entidad. Los objetivos inactivos se conservan en registros históricos, pero no pueden utilizarse para crear, reasignar ni activar metas.

Cada indicador define una línea base, un valor objetivo, un sentido de medición ascendente o descendente y una ponderación dentro de su meta. Las ponderaciones de los indicadores activos de una meta deben sumar `100 %`. La validación de la ficha confirma que la definición del indicador es adecuada, pero no significa que la meta ya se haya cumplido.

### Expediente, revisión y seguimiento

El planificador construye el expediente mientras el plan se encuentra en `BORRADOR`, `DEVUELTO` o `RECHAZADO`. Antes del envío, el sistema comprueba su descripción, responsable, periodo, objetivos, alineaciones, metas activas, indicadores y ponderaciones. Los bloqueos se muestran dentro del detalle del plan y también se aplican en el backend.

Cuando un supervisor pulsa **Iniciar revisión**, queda asignado al expediente. Ese supervisor —o el superadministrador mediante su bypass explícito— puede validar las alineaciones y fichas de indicadores, devolver el plan, aprobarlo o rechazarlo. La aprobación exige que el expediente esté completo y que sus validaciones pendientes hayan sido resueltas.

Los avances solo pueden registrarse después de aprobar el plan, sobre indicadores activos y con ficha validada. El sistema conserva evidencia, fecha, valor y usuario de cada medición, y calcula:

- progreso respecto de la línea base y el valor objetivo;
- avance esperado según la fecha y frecuencia;
- tendencia y próxima medición;
- estados `PENDIENTE_VALIDACION`, `SIN_AVANCES`, `EN_CURSO`, `EN_RIESGO`, `CUMPLIDO` e `INCUMPLIDO`;
- consolidación ponderada por meta, objetivo estratégico y plan.

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
| Planes        | Expediente, validación estructural, revisión asignada, decisiones y seguimiento |
| Metas         | Resultados por objetivo, ponderación de indicadores y cumplimiento consolidado   |
| Indicadores   | Ficha técnica, validación, mediciones, evidencia, tendencia y seguimiento        |
| Objetivos     | Objetivos estratégicos y consulta de metas y alineaciones vinculadas              |
| Alineación    | Catálogos PND/ODS, matriz estratégica, uso real y validación durante la revisión  |
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

En una instalación existente, la migración vincula automáticamente una meta cuando su entidad tiene un único objetivo estratégico activo. Si encuentra una relación ambigua, se detiene antes de imponer el campo obligatorio para evitar asignaciones incorrectas; en ese caso deben vincularse primero las metas pendientes y volver a ejecutar `python manage.py migrate`.

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
| `/planes/:planId`          | `planes.ver`        |
| `/metas`                   | `metas.ver`         |
| `/indicadores`             | `indicadores.ver`   |
| `/indicadores/:indicatorId` | `indicadores.ver`  |
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

### Acciones de planificación y seguimiento

```text
GET  /api/planes/<id>/expediente/
GET  /api/planes/<id>/seguimiento/
GET  /api/planes/<id>/validacion/
GET  /api/planes/<id>/historial/
POST /api/planes/<id>/enviar-a-revision/
POST /api/planes/<id>/revisar/
POST /api/planes/<id>/devolver/
POST /api/planes/<id>/aprobar/
POST /api/planes/<id>/rechazar/
POST /api/planes/<id>/archivar/

GET  /api/metas/<id>/seguimiento/

GET  /api/indicadores/<id>/seguimiento/
POST /api/indicadores/<id>/validar/
POST /api/indicadores/<id>/registrar-avance/

POST /api/alineaciones/<id>/validar/
POST /api/alineaciones/<id>/rechazar/
```

## Roles y alcance

| Rol base                    | Alcance general                                        |
| --------------------------- | ------------------------------------------------------ |
| Administrador del Sistema   | Administración global                                  |
| Planificador Institucional  | Registros propios o asignados dentro de su institución |
| Supervisor de Planificación | Institución propia, bandeja enviada a revisión y expedientes asignados |
| Usuario Externo             | Únicamente su institución                              |
| Auditor / Control Interno   | Lectura dentro de su institución                       |
| Superadministrador técnico  | Acceso técnico total excepcional                       |

La autorización se decide mediante códigos de permiso. Un usuario o rol inactivo no otorga permisos, y un administrador ordinario no puede delegar permisos superiores a los propios ni modificar el rol técnico protegido.

## Validación manual recomendada

1. Sin iniciar sesión, abra `/dashboard` y confirme la redirección a `/login`. Pruebe también una contraseña incorrecta, el cierre de sesión, una ruta inexistente y una ruta sin permiso.
2. Inicie sesión con cada usuario local y confirme que el menú, el panel y las acciones corresponden a sus permisos efectivos.
3. Con `administrador`, revise usuarios, roles, entidades y unidades. Compruebe la dependencia entre entidad y unidad, la protección del rol técnico y el bloqueo controlado de cuentas.
4. Con `planificador`, cree un objetivo estratégico, una alineación PND/ODS en borrador y un plan identificable.
5. Abra el expediente del plan antes de completarlo y confirme que muestra los bloqueos que impiden enviarlo.
6. Cree una meta vinculada con el objetivo de la misma entidad, actívela y agregue indicadores activos cuyas ponderaciones sumen `100 %`.
7. Regrese al expediente y envíelo a revisión cuando desaparezcan los bloqueos de envío.
8. Con `supervisor`, abra el plan recibido, revise su descripción y cadena completa, pulse **Iniciar revisión**, valide la alineación y luego pulse **Validar ficha** dentro del seguimiento del indicador.
9. Regrese al expediente y pruebe **Aprobar plan**. Para comprobar correcciones, repita el flujo con otro plan y utilice **Devolver para corrección** o **Rechazar plan**, registrando una observación.
10. Con `planificador`, abra un indicador del plan aprobado y registre avances con fecha, valor, observación y referencia de evidencia. Compruebe el progreso en el indicador, la meta, el objetivo, el plan y el dashboard.
11. Con `externo` y `auditor`, confirme que no se muestren registros de otras instituciones. El Auditor debe disponer únicamente de consultas, reportes y trazabilidad.
12. Genere vistas previas y exportaciones desde Reportes, revise los eventos en Auditoría y compruebe el comportamiento responsive reduciendo el ancho del navegador.

Para probar la creación de metas, el plan debe encontrarse en un estado editable: `BORRADOR`, `DEVUELTO` o `RECHAZADO`.

## Pruebas automatizadas

Las pruebas están incluidas en el repositorio y se ejecutan desde PowerShell o la terminal de Visual Studio Code. No son comandos para Postman ni opciones de la interfaz de SIPeIP.

### Preparación y carpeta de ejecución

Debe tener Python y el entorno virtual del backend con las dependencias de `backend/requirements.txt` instaladas y su configuración local preparada, como se explica en [Configurar el backend](#2-configurar-el-backend). Si ya utiliza la aplicación, no necesita reinstalarla. La configuración de pruebas también lee `backend/.env`: debe tener una `SECRET_KEY` local configurada o `DEBUG=True` para que se genere una clave efímera de desarrollo. No comparta ese archivo ni sus credenciales.

Abra una terminal en la raíz del repositorio, donde se encuentran `README.md`, `backend` y `frontend`, y ejecute:

```powershell
cd backend
```

Todos los comandos de esta sección se ejecutan desde esa carpeta, que contiene `manage.py`. Si ya está en `backend`, no repita `cd backend`. Los ejemplos utilizan directamente el Python de `.venv`, por lo que no requieren activar el entorno virtual ni cambiar la política de ejecución de PowerShell.

Con `--settings=config.settings_test`, las pruebas utilizan SQLite en memoria. Crean sus propios usuarios, instituciones y registros temporales, aplican las migraciones a esa base y la destruyen al terminar. No modifican los datos habituales de la aplicación.

No necesita iniciar PostgreSQL, ejecutar `runserver` o `npm run dev`, abrir Postman ni ejecutar `inicializar_sistema` o `migrate` previamente para estas pruebas. Mantenga `--settings=config.settings_test` en los comandos para utilizar la configuración aislada.

### Ejecutar todas las pruebas

```powershell
.\.venv\Scripts\python.exe manage.py test --settings=config.settings_test --verbosity 2
```

La suite actual contiene 23 pruebas. La opción `--verbosity 2` muestra el nombre y el resultado de cada una. Al principio aparecerán mensajes de creación de la base temporal y aplicación de migraciones. Si todas pasan, el resumen tendrá esta forma; el tiempo de ejecución puede variar:

```text
Found 23 test(s).
...
Ran 23 tests in ...

OK
Destroying test database for alias 'default' ...
```

### Ejecutar una prueba indicada en el Excel

La referencia `SipeipApiEssentialTests.test_reporte_no_filtra_datos_de_otra_institucion` identifica una clase y un método del archivo `backend/tests/test_api_essential.py`. Para ejecutar únicamente ese caso:

```powershell
.\.venv\Scripts\python.exe manage.py test tests.test_api_essential.SipeipApiEssentialTests.test_reporte_no_filtra_datos_de_otra_institucion --settings=config.settings_test --verbosity 2
```

Comprueba que el reporte de planes de un usuario externo excluye registros de otra institución y que cambiar el filtro `entidad` no permite obtenerlos. El resultado esperado incluye el nombre de la prueba seguido de `ok` y termina con:

```text
Ran 1 test in ...

OK
```

Para otro caso del Excel, consulte las columnas **Archivo** y **Clase y método** de la hoja **Pruebas automatizadas**. Convierta el archivo en su módulo de Python: quite `backend/` y `.py`, y sustituya `/` por `.`. Añada un punto y la clase y método indicados. Esa referencia completa sustituye a `tests.test_api_essential.SipeipApiEssentialTests.test_reporte_no_filtra_datos_de_otra_institucion` en el comando anterior; conserve las demás opciones.

### Localizar las pruebas y ejecutar el flujo funcional

| Archivo | Comprobaciones |
| --- | --- |
| [test_api_essential.py](backend/tests/test_api_essential.py) | Sesión, CSRF, permisos, aislamiento institucional, relaciones, transiciones, eliminación protegida y reportes. |
| [test_flujo_planificacion_funcional.py](backend/tests/test_flujo_planificacion_funcional.py) | Flujo de creación, alineación, revisión, validación, aprobación y seguimiento de un plan mediante la API, con sesión y CSRF. |
| [test_seguimiento_metas.py](backend/tests/test_seguimiento_metas.py) | Cálculo de progreso, cierre de metas y conservación de datos durante la migración de seguimiento. |

Para ejecutar solo el flujo funcional de planificación:

```powershell
.\.venv\Scripts\python.exe manage.py test tests.test_flujo_planificacion_funcional --settings=config.settings_test --verbosity 2
```

Actualmente ese archivo contiene un caso que recorre el flujo completo; el resumen esperado es `Ran 1 test` y `OK`. También puede ejecutar los otros archivos utilizando `tests.test_api_essential` o `tests.test_seguimiento_metas` en lugar de `tests.test_flujo_planificacion_funcional`.

### Interpretar y conservar el resultado

- `ok` junto a un caso: sus comprobaciones pasaron.
- `OK` al final: las pruebas ejecutadas terminaron correctamente. Confirme también la cantidad de casos; `Ran 0 tests` no verifica ninguno. Si se informa `skipped`, esos casos fueron omitidos y no deben registrarse como superados.
- `FAIL`: una comprobación obtuvo un resultado distinto al esperado. El detalle identifica el caso y la comparación que falló.
- `ERROR`: una prueba no pudo completarse por una excepción o un problema de preparación. Revise el mensaje y el archivo indicados antes de repetirla.

El mensaje `System check identified no issues` corresponde a la revisión de configuración de Django; por sí solo no confirma que las pruebas hayan pasado.

Si no se encuentra `manage.py`, compruebe que la terminal esté en `backend`. Si no existe `.venv` o aparece `No module named django`, revise la instalación del entorno y sus dependencias. Si se solicita `SECRET_KEY`, revise la configuración local descrita al inicio de esta sección.

Para conservar evidencia, guarde la salida de la terminal junto con el comando, la fecha y la versión utilizada. Puede consultar la versión con `git rev-parse --short HEAD`. No adjunte `.env` ni credenciales. El estado **Superada** del Excel corresponde a la ejecución registrada en su fecha y no se actualiza automáticamente al repetir estos comandos.

Esta suite comprueba los casos definidos en el backend, incluido el flujo funcional por API. No abre un navegador ni verifica el diseño visual. Las comprobaciones de pantallas, formularios y navegación se realizan con la [validación manual recomendada](#validación-manual-recomendada). La ejecución con SQLite tampoco sustituye una validación específica sobre PostgreSQL.

## Pruebas manuales con Postman

La colección Postman reproducible se encuentra en:

```text
docs/postman/SIPeIP_Flujo_Planificacion_Funcional.postman_collection.json
```

Contiene 42 solicitudes organizadas para preparar la sesión, construir un expediente, iniciar la revisión, validar, aprobar, registrar seguimiento y comprobar aislamiento institucional. Debe ejecutarse en orden y solo requiere completar la variable `password` con la contraseña usada en `inicializar_sistema`; esa contraseña permanece vacía en el archivo versionado.

La explicación manual de cada solicitud está disponible en:

```text
docs/Entregable_3_Guia_Pruebas_Postman_SIPeIP.tex
```

## Comprobaciones del proyecto

### Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --settings=config.settings_test
```

La configuración `config.settings_test` crea una base temporal en memoria y no modifica los registros de `sipeip_db`.

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
