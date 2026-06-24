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
