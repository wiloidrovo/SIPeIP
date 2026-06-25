# SIPeIP

Sistema web para la gestión de usuarios, roles, planes, proyectos, objetivos, reportes y auditoría, desarrollado como parte del proceso de implementación del proyecto SIPeIP.

## Stack tecnológico

- Frontend: React + Vite + TypeScript
- Backend: Django + Django REST Framework
- Base de datos: PostgreSQL
- Control de versiones: Git + GitHub
- Pipeline: GitHub Actions

## Estado actual

El proyecto se encuentra en fase inicial de implementación. Actualmente se ha configurado el backend con Django, conexión a PostgreSQL y los módulos base del Sprint 1:

- Gestión de usuarios
- Gestión de roles

## Estructura del proyecto

```text
SIPeIP/
├── backend/
│   ├── apps/
│   │   ├── usuarios/
│   │   └── roles/
│   ├── config/
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
├── docs/
├── .github/
│   └── workflows/
└── README.md
```

## Configuración del backend

Entrar a la carpeta del backend:

```bash
cd backend
```

Crear entorno virtual:

```bash
py -3.11 -m venv .venv
```

Activar entorno virtual en Windows PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```bash
python -m pip install -r requirements.txt
```

Crear un archivo `.env` dentro de la carpeta `backend` tomando como base el archivo `.env.example`.

Ejemplo de variables requeridas:

```env
SECRET_KEY=change-me
DEBUG=True

DB_NAME=sipeip_db
DB_USER=sipeip_user
DB_PASSWORD=change-me
DB_HOST=localhost
DB_PORT=5432
```

Ejecutar migraciones:

```bash
python manage.py migrate
```

Crear superusuario:

```bash
python manage.py createsuperuser
```

Levantar servidor:

```bash
python manage.py runserver
```

Acceso local:

```text
http://127.0.0.1:8000/
```

Panel administrativo:

```text
http://127.0.0.1:8000/admin/
```

## Módulos iniciales

### Usuarios

Permite administrar usuarios del sistema y mantener información básica como estado, rol y datos de acceso.

### Roles

Permite administrar los roles del sistema, los cuales serán utilizados para organizar permisos y responsabilidades.

## Arquitectura

El sistema se organiza bajo una arquitectura web cliente-servidor con separación entre frontend, backend y base de datos.

```text
Browser → React Frontend → Django REST API → PostgreSQL
```

A nivel de código, el backend mantiene separación entre modelo, controlador y persistencia mediante Django y Django REST Framework. El frontend se desarrollará como la vista principal de interacción con el usuario.

## Sprint actual

Sprint 1:

- Gestión de usuarios
- Gestión de roles

## Evidencia técnica actual

Hasta el momento, el proyecto cuenta con:

- Entorno virtual de Python configurado.
- Proyecto Django creado.
- Conexión a PostgreSQL configurada.
- Modelos iniciales de Usuario y Rol.
- Migraciones aplicadas.
- Panel administrativo de Django funcionando.
- Registro de módulos Usuarios y Roles en el panel administrativo.

## Próximos pasos

- Implementar serializers para usuarios y roles.
- Implementar controladores CRUD con Django REST Framework.
- Configurar rutas de API.
- Crear frontend con React + Vite + TypeScript.
- Implementar pantallas iniciales para usuarios y roles.
- Agregar pruebas básicas del backend.
- Configurar pipeline inicial con GitHub Actions.
