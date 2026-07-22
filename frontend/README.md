# Frontend de SIPeIP

Aplicación web de SIPeIP construida con React, TypeScript, React Router y Vite.

La interfaz utiliza un layout institucional común, rutas protegidas, navegación condicionada por permisos y módulos separados para autenticación, administración, planificación, alineación, proyectos, reportes y auditoría.

## Requisitos

- Node.js 18 o superior
- npm
- API de Django disponible en `http://localhost:8000`

## Instalación

```powershell
cd frontend
npm ci
```

## Desarrollo

```powershell
npm run dev
```

La aplicación queda disponible en `http://localhost:5173`.

## Compilación

```powershell
npm run build
```

El comando ejecuta la comprobación de TypeScript y genera el paquete de producción en `dist/`. Ese directorio es un artefacto local y no se versiona.

## Organización

```text
src/
├── app/          Router principal
├── auth/         Sesión, rutas y guardas de permisos
├── components/   Componentes reutilizables
├── layouts/      Layout y navegación institucional
├── modules/      Módulos funcionales
├── pages/        Páginas generales
├── services/     Cliente de la API
├── styles/       Estilos compartidos
└── utils/        Validaciones y utilidades
```

Todas las solicitudes utilizan la sesión del backend mediante cookies y `credentials: "include"`. Las operaciones de escritura envían el token CSRF; la autorización efectiva siempre se verifica nuevamente en Django REST Framework.

La instalación completa, los usuarios locales, las rutas y el recorrido de validación se documentan en el [README principal](../README.md).
