# CONVENTIONS — Estándares de la consultora

> Estas convenciones aplican a todos los proyectos y todos los clientes.
> Son la capa de mayor prioridad después de GLOBAL_RULES.

## Convenciones de código

### Nomenclatura
- Variables y funciones: `camelCase` (JS/TS) / `snake_case` (Python)
- Clases y componentes: `PascalCase`
- Constantes: `UPPER_SNAKE_CASE`
- Archivos: `kebab-case` para componentes, `snake_case` para módulos Python

### Estructura de commits (Conventional Commits)
```
<tipo>(<scope>): <descripción corta>

Tipos válidos: feat, fix, refactor, docs, test, chore, perf
Ejemplo: feat(auth): agregar soporte OAuth2 para Apple
```

### Tamaño de funciones
- Máximo 30 líneas por función
- Si supera 30 líneas: extraer en funciones auxiliares

### Comentarios
- Comentar el "por qué", no el "qué"
- TODO con ticket: `// TODO(TASK-142): refactorizar cuando...`

## Convenciones de API

### REST
- Recursos en plural: `/api/orders`, `/api/users`
- Versioning en header: `API-Version: 1`
- Paginación: `?page=1&limit=20`
- Errores: `{ "error": "mensaje", "code": "ERROR_CODE" }`

### Respuestas HTTP
- 200: OK
- 201: Creado
- 400: Error de validación (incluir detalle)
- 401: No autenticado
- 403: Sin permisos
- 404: No encontrado
- 500: Error interno (nunca exponer stack trace)

## Convenciones de base de datos

- Nombres de tablas: `snake_case` en plural
- PKs: `id` (UUID v4 preferido)
- Timestamps: `created_at`, `updated_at` en todas las tablas
- Soft delete: columna `deleted_at` nullable
- Migraciones: numeradas y con descripción (`0001_create_users_table.sql`)
