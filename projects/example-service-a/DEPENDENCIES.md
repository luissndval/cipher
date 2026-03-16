# DEPENDENCIES.md — auth-service
> Última actualización: 2024-01-15
> Ver `schemas/dependency-schema.md` para el formato completo de cada campo.

---

## Dependencias de salida (auth-service llama a / escribe en)

| Destino | Tipo | Protocolo | Contrato | Versión | Campos críticos | SLA esperado |
|---------|------|-----------|----------|---------|-----------------|--------------|
| PostgreSQL (auth-db) | sync | SQL/TCP | Esquema en `db/migrations/` | Schema v14 | `users.user_id`, `users.password_hash`, `users.status`, `refresh_tokens.token_hash`, `refresh_tokens.family_id` | p99 < 20ms |
| Redis (session-cache) | sync | RESP | Keys documentadas en `docs/redis-keys.md` | Redis 7.x | `rate_limit:{ip}`, `rate_limit:{user_id}`, `session:{refresh_token_hash}` | p99 < 5ms |
| email-service | async | HTTP REST | OpenAPI en `email-service/api/v1/openapi.yaml` | v1 | `to`, `template_id`, `variables.verification_token`, `variables.user_name` | best-effort, entrega < 5 min |
| oauth-provider (Google) | sync | OIDC/HTTPS | Google Identity Platform OIDC spec | OpenID Connect 1.0 | `sub` (Google user ID), `email`, `email_verified` | p99 < 500ms |
| oauth-provider (GitHub) | sync | OAuth 2.0/HTTPS | GitHub OAuth Apps spec | OAuth 2.0 | `id` (GitHub user ID), `email`, `login` | p99 < 500ms |

### Notas de dependencias de salida

- **PostgreSQL (auth-db):** Base de datos exclusiva de auth-service. Ningún otro servicio tiene acceso directo. Conexión a través de `DATABASE_URL` con pool de máximo 20 conexiones. Si la DB no responde en 3s, el endpoint falla con 503. No hay caché de datos de usuario — siempre se lee de DB para garantizar consistencia en operaciones de seguridad.

- **Redis (session-cache):** Usado únicamente para rate limiting y blacklist de tokens revocados. Si Redis no está disponible, el sistema DEBE fallar abierto para rate limiting (permitir el request) pero fallar CERRADO para validación de tokens revocados (rechazar el token). Ver `src/redis/fallback.py` para la lógica de fallback.

- **email-service:** Comunicación asíncrona via HTTP. Si el email-service no responde, el registro del usuario se completa pero se marca `email_sent=false` en DB. Un job background (`workers/retry-emails.py`) reintenta cada 5 minutos por hasta 24 horas. Un usuario con `email_sent=false` no puede hacer login (estado `PENDING_VERIFICATION` permanece) hasta que el email sea enviado y el usuario verifique.

- **oauth-provider (Google/GitHub):** Si el proveedor OAuth falla, el login social falla pero el login con email/contraseña no se ve afectado. Los tokens OAuth de Google/GitHub NUNCA se almacenan — sólo se usan para extraer el `sub`/`id` y el `email` en el momento del login.

---

## Dependencias de entrada (quién llama a auth-service)

| Origen | Tipo | Protocolo | Contrato que expone | Campos críticos que consume |
|--------|------|-----------|---------------------|-----------------------------|
| api-gateway | sync | HTTP REST | `/api/v1/auth/**` (OpenAPI en `docs/api/openapi.yaml`) | `Authorization: Bearer <token>` para validación |
| Todos los microservicios internos | sync | HTTP REST | `GET /internal/validate` | `user_id`, `roles` (del payload del token) |
| frontend-web | sync | HTTP REST | `/api/v1/auth/**` | `access_token`, `refresh_token`, `user_id` |
| mobile-app (iOS/Android) | sync | HTTP REST | `/api/v1/auth/**` | `access_token`, `refresh_token`, `user_id` |

### Notas de dependencias de entrada

- **api-gateway:** Actúa como proxy. Añade el header `X-Request-ID` a todos los requests. auth-service DEBE propagar este ID en logs y respuestas de error para trazabilidad.

- **Servicios internos (endpoint `/internal/validate`):** Este endpoint es llamado en cada request autenticado de todos los servicios. Su latencia impacta DIRECTAMENTE la latencia de toda la plataforma. El p99 de `/internal/validate` DEBE ser < 10ms. La validación de JWT es local (no requiere DB lookup) excepto para tokens revocados (requiere Redis).

---

## Eventos que EMITE

| Nombre del evento | Topic/Queue | Schema | Consumidores conocidos | Trigger |
|-------------------|-------------|--------|------------------------|---------|
| `user.registered` | `auth.events.user.registered` | `schemas/events/user-registered.json` | user-profile-service, email-service (welcome email), analytics-service | Usuario completa registro y verifica email |
| `user.login` | `auth.events.user.login` | `schemas/events/user-login.json` | analytics-service, fraud-detection-service | Login exitoso |
| `user.login.failed` | `auth.events.security.login-failed` | `schemas/events/login-failed.json` | fraud-detection-service, security-monitoring | 3+ intentos fallidos consecutivos |
| `user.password.changed` | `auth.events.user.password-changed` | `schemas/events/password-changed.json` | email-service (notificación), security-monitoring | Cambio exitoso de contraseña |
| `user.account.locked` | `auth.events.security.account-locked` | `schemas/events/account-locked.json` | email-service (alerta), security-monitoring | Cuenta bloqueada por intentos fallidos |
| `session.revoked_all` | `auth.events.security.all-sessions-revoked` | `schemas/events/sessions-revoked.json` | fraud-detection-service | Reutilización de refresh token detectada |

---

## Eventos que CONSUME

auth-service no consume eventos de otros servicios. Opera únicamente en modo request/response.

---

## Advertencias críticas

1. **Redis como single point of failure para revocación de tokens:** Si Redis está caído, el endpoint `/internal/validate` no puede verificar si un refresh token fue revocado. La lógica de fallback actual (en `src/redis/fallback.py`) acepta tokens que no pueden verificarse en Redis. Esto significa que en caso de caída de Redis, tokens recién revocados pueden seguir siendo aceptados durante el tiempo de caída. **Nunca cambiar esta lógica de fallback sin análisis de seguridad.**

2. **El campo `password_hash` nunca debe aparecer en respuestas API ni logs:** El modelo SQLAlchemy `User` tiene `password_hash` marcado con `load_only=True`. Si se agrega un nuevo endpoint que serializa objetos `User`, verificar que este campo esté excluido explícitamente.

3. **Los refresh tokens se almacenan como HASH (SHA-256) en DB, nunca en texto plano:** La tabla `refresh_tokens` almacena `token_hash = sha256(token_value)`. Si se necesita buscar un refresh token, siempre hashear primero. Ver `src/tokens/repository.py:find_by_value()`.

4. **Migraciones de DB requieren coordinación:** La tabla `users` es referenciada por foreign key en al menos 8 otros servicios que tienen su propia DB. Cambios de schema en `users` (especialmente `user_id` o `status`) requieren coordinación con esos servicios antes de migrar.
