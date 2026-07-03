# SIPeIP

Sistema web para la gestión de usuarios, roles, planes, proyectos, objetivos, reportes y auditoría, desarrollado como parte del proceso de implementación del proyecto SIPeIP.

## Stack tecnológico

- **Frontend**: React 18+ con Vite, TypeScript y Vanilla CSS.
- **Backend**: Django 5.2+ con Django REST Framework.
- **Base de datos**: PostgreSQL.
- **Control de versiones**: Git + GitHub.
- **Pipeline**: GitHub Actions.

## Arquitectura

El sistema se organiza bajo una arquitectura web cliente-servidor con separación clara entre responsabilidades:

```text
Navegador Cliente → React (Frontend SPA) → Django REST API (Backend) → PostgreSQL (Base de datos)
```

A nivel de código, el backend mantiene separación entre modelo, controlador y persistencia mediante el patrón de diseño implementado por Django. El frontend interactúa exclusivamente mediante peticiones HTTP asíncronas a la API REST.

## Estado actual: Sprint 1

El proyecto ha completado los componentes base del Sprint 1, correspondientes al acceso y seguridad del sistema:

- **Gestión de usuarios**: Registro, edición, activación, desactivación y bloqueo de usuarios.
- **Gestión de roles**: Creación, actualización, control de estados y asignación granular de permisos del sistema.

## Estructura del proyecto

```text
SIPeIP/
├── backend/
│   ├── apps/
│   │   ├── roles/       # Módulo de administración de roles y permisos
│   │   └── usuarios/    # Módulo de usuarios y autenticación base
│   ├── config/          # Configuración core de Django y enrutamiento
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── services/    # Clientes HTTP para consumo de API
│   │   ├── utils/       # Lógica compartida y validaciones
│   │   ├── App.tsx      # Interfaz y componente principal
│   │   └── index.css    # Estilos globales y reseteo
│   ├── package.json
│   └── vite.config.ts
├── docs/                # Documentación adicional del proyecto
├── .github/             # Configuración de flujos CI/CD
└── README.md
```

## Prerrequisitos

Para ejecutar el entorno de desarrollo local, se requiere:

- **Python** 3.11 o superior.
- **Node.js** 18 o superior.
- **PostgreSQL** instalado y ejecutándose (puerto por defecto 5432).

## Configuración del entorno de desarrollo

### 1. Base de datos

Asegúrese de crear una base de datos PostgreSQL y disponer de credenciales válidas antes de iniciar el backend.

### 2. Configuración del Backend (Django)

Desde la raíz del proyecto, acceda a la carpeta del backend:

```bash
cd backend
```

Cree y active el entorno virtual (comandos para Windows PowerShell):

```bash
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instale las dependencias del sistema:

```bash
python -m pip install -r requirements.txt
```

Cree un archivo `.env` basado en la plantilla:

```bash
copy .env.example .env
```

Asegúrese de actualizar el archivo `.env` con las credenciales de su base de datos PostgreSQL local:

```env
SECRET_KEY=su-clave-secreta-segura
DEBUG=True

DB_NAME=sipeip_db
DB_USER=su_usuario_pg
DB_PASSWORD=su_password_pg
DB_HOST=localhost
DB_PORT=5432
```

Ejecute las migraciones iniciales de la base de datos:

```bash
python manage.py migrate
```

Cree un superusuario para acceso total:

```bash
python manage.py createsuperuser
```

Inicie el servidor de desarrollo en `http://127.0.0.1:8000/`:

```bash
python manage.py runserver
```

El panel administrativo nativo de Django está disponible en `http://127.0.0.1:8000/admin/`.

### 3. Configuración del Frontend (React + Vite)

Abra una nueva terminal, y desde la raíz del proyecto acceda a la carpeta del frontend:

```bash
cd frontend
```

Instale las dependencias de Node:

```bash
npm install
```

Inicie el servidor de desarrollo, por defecto en `http://localhost:5173/`:

```bash
npm run dev
```

Para generar la versión de producción (build), ejecute:

```bash
npm run build
```
