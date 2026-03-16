# TECHNICAL_STATE — auth-service
> Última actualización: 2026-03-16 | Actualizado por: brain-agent (init)

## Endpoints activos

| Método | Path | Request | Response | Códigos de respuesta |
|--------|------|---------|----------|----------------------|
| POST | /auth/login | `{ email, password }` | `{ access_token, refresh_token, expires_in }` | 200, 400, 401, 429 |
| POST | /auth/logout | `{ refresh_token }` | `{ message }` | 200, 401 |
| POST | /auth/refresh | `{ refresh_token }` | `{ access_token, expires_in }` | 200, 401 |
| POST | /auth/register | `{ email, password, name }` | `{ user_id, message }` | 201, 400, 409 |
| GET  | /auth/me | — (JWT header) | `{ user_id, email, name, roles }` | 200, 401 |
| POST | /auth/password/reset-request | `{ email }` | `{ message }` | 200, 404 |
| POST | /auth/password/reset | `{ token, new_password }` | `{ message }` | 200, 400, 410 |

## Integraciones activas

| Sistema | Estado | Versión contrato | Último cambio | Notas |
|---------|--------|-----------------|---------------|-------|
| PostgreSQL (users DB) | ✓ activo | schema v2.1 | 2026-03-10 | Pool de 10 conexiones |
| Redis (sessions) | ✓ activo | — | 2026-02-28 | TTL 3600s por sesión |
| SendGrid (emails) | ✓ activo | API v3 | 2026-03-01 | Solo para reset de password |
| OAuth Google | ✓ activo | OAuth 2.0 | 2026-01-15 | Callback: /auth/oauth/google/callback |

## Modelos de datos vigentes

| Modelo | Versión | Campos clave | Último cambio |
|--------|---------|-------------|---------------|
| User | v2.1 | id, email, password_hash, roles[], status, created_at | 2026-03-10 |
| Session | v1.0 | session_id, user_id, refresh_token_hash, expires_at | 2026-02-28 |
| PasswordResetToken | v1.0 | token_hash, user_id, expires_at, used | 2026-03-01 |

## Cambios recientes con impacto

- 2026-03-10 [users DB] Migración schema v2.0 → v2.1: campo `roles[]` reemplaza `role` (string) — consumidores deben actualizar lectura de roles
- 2026-03-01 [reset password] Nuevo endpoint POST /auth/password/reset-request — no breaking

## Estado de salud por módulo

| Módulo | Estado | Observaciones |
|--------|--------|---------------|
| Login / JWT | ✓ estable | Rate limit: 10 intentos/min por IP |
| Register | ✓ estable | Validación de email único en DB |
| OAuth Google | ✓ estable | Requiere GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET |
| Password Reset | ✓ estable | Token expira en 15 min |
| Redis Sessions | ✓ estable | Monitorear memoria en pico de sesiones |
