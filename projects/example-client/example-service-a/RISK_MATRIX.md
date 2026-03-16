# RISK_MATRIX.md — auth-service
> Última actualización: 2024-01-15
> Ver `schemas/risk-schema.md` para criterios de asignación de nivel.

---

## Niveles de riesgo

| Nivel | Criterio | Acción requerida |
|-------|----------|------------------|
| **CRÍTICO** | Afecta autenticación, tokens, contraseñas, o puede comprometer cuentas de usuario | Aprobación de Platform Security Lead + plan de rollback + notificación al equipo de seguridad |
| **ALTO** | Afecta flujos de login/registro, rate limiting, o sesiones activas de usuarios | Análisis de impacto completo + aprobación de tech lead + pruebas de integración |
| **MEDIO** | Cambios en lógica secundaria, validaciones no críticas, o mejoras de rendimiento | Revisión de impacto + pruebas unitarias + review de PR |
| **BAJO** | Cambios en logs, comentarios, documentación, o refactoring sin cambio de comportamiento | Verificación de que tests existentes pasan |

---

## Componentes del servicio y su nivel de riesgo

| Componente | Nivel | Justificación | Revisar antes de cambiar |
|------------|-------|---------------|--------------------------|
| Emisión de JWT (access tokens) | CRÍTICO | Un error aquí puede emitir tokens inválidos para toda la plataforma o tokens con permisos incorrectos | `src/tokens/jwt_service.py`, `tests/unit/test_jwt_service.py`, BR-001, BR-002 |
| Hash de contraseñas (bcrypt) | CRÍTICO | Un cambio incorrecto puede almacenar contraseñas sin hash o con hash débil | `src/auth/password_service.py`, `tests/unit/test_password_service.py`, BR-003, BR-004, INV-003 |
| Validación de tokens (`/internal/validate`) | CRÍTICO | Llamado por todos los servicios; un error puede denegar acceso a toda la plataforma o aceptar tokens inválidos | `src/api/internal/validate.py`, `tests/integration/test_validate_endpoint.py`, DEPENDENCIES.md |
| Revocación de refresh tokens y detección de reutilización | CRÍTICO | Fallas aquí permiten que atacantes con tokens robados mantengan acceso | `src/tokens/refresh_service.py`, `src/redis/session_store.py`, BR-002 |
| Rate limiting (Redis) | ALTO | Si se deshabilita o rompe, la plataforma queda expuesta a fuerza bruta | `src/middleware/rate_limiter.py`, `src/redis/rate_limit_store.py`, BR-005 |
| Flujo de registro de usuario | ALTO | Errores pueden crear usuarios en estado inválido o sin verificación de email | `src/api/v1/register.py`, `tests/integration/test_registration.py`, BR-006 |
| Flujo de login (email/password) | ALTO | Errores pueden bloquear todos los usuarios o permitir acceso sin credenciales válidas | `src/api/v1/login.py`, `tests/integration/test_login.py` |
| Flujo de OAuth (Google/GitHub) | ALTO | Errores pueden permitir login con accounts OAuth sin verificar email | `src/oauth/google_handler.py`, `src/oauth/github_handler.py`, `tests/integration/test_oauth.py` |
| Recuperación de contraseña (forgot password) | ALTO | Token de reset comprometido permite tomar control de cuenta | `src/api/v1/password_reset.py`, `tests/integration/test_password_reset.py` |
| Gestión de sesiones (listar/revocar) | MEDIO | Errores afectan UX pero no comprometen seguridad directamente si la revocación falla gracefully | `src/api/v1/sessions.py`, `tests/unit/test_sessions.py` |
| Bloqueo y desbloqueo de cuentas | MEDIO | Puede causar DoS sobre usuarios específicos si hay bug, pero no compromete credenciales | `src/auth/account_lock_service.py` |
| Emisión de eventos (Kafka) | MEDIO | Falla en eventos no impacta el flujo de autenticación principal, pero sí servicios downstream | `src/events/publisher.py`, DEPENDENCIES.md (sección Eventos) |
| Logs del servicio | BAJO | Los logs no afectan comportamiento. Verificar que no se loguean datos sensibles (RO-002) | `src/logging/`, RO-002 |
| Documentación de API (OpenAPI spec) | BAJO | Sólo afecta documentación | `docs/api/openapi.yaml` |

---

## Reglas de escalamiento

### Cuándo escalar al Platform Security Lead

- Cualquier cambio en componentes clasificados como **CRÍTICO** debe revisarse con el Platform Security Lead antes de implementar, sin excepción.
- Cualquier cambio que afecte el algoritmo de hash de contraseñas.
- Cualquier cambio en la duración de tokens (BR-001) o en la política de rotación (BR-002).
- Detección de una vulnerabilidad de seguridad, aunque sea teórica.

### Procedimiento de rollback por nivel

| Nivel | Procedimiento de rollback |
|-------|---------------------------|
| CRÍTICO | 1. Revertir deploy inmediatamente (< 5 min). 2. Notificar a Platform Security Lead y Engineering Manager. 3. Si tokens inválidos fueron emitidos: rotación de secreto JWT (invalida TODOS los tokens activos — coordinar con todos los servicios). 4. Post-mortem en 48 horas. |
| ALTO | 1. Revertir deploy. 2. Verificar que flujos principales funcionan. 3. Notificar al tech lead. 4. Analizar si usuarios afectados necesitan acción (e.g., reset de sesiones). |
| MEDIO | Revertir commit + re-deploy. Verificar con smoke tests. |
| BAJO | Revertir commit. |

### Rotación del secreto JWT (procedimiento de emergencia)

La rotación del secreto JWT invalida **todos** los tokens activos de **todos** los usuarios de **toda** la plataforma. Usar sólo como último recurso.

1. Notificar a los tech leads de todos los servicios que consumen `/internal/validate`.
2. Actualizar `JWT_SECRET` en los secrets del ambiente afectado.
3. Reiniciar auth-service con el nuevo secreto.
4. Los usuarios serán deslogueados y deberán hacer login nuevamente.
5. Monitorear métricas de login durante 30 minutos post-rotación.

---

## Historial de incidentes relacionados

| Fecha | Componente afectado | Causa raíz | Lección aprendida |
|-------|---------------------|------------|-------------------|
| 2023-08-14 | Rate limiting (Redis) | Migración de Redis sin configurar el nuevo host en env vars | Rate limiting deshabilitado por 45 min. Implementar health check de Redis en startup. |
| 2023-11-02 | Emisión de eventos (Kafka) | Schema de evento `user.registered` cambió sin actualizar `user-profile-service` | user-profile-service dejó de crear perfiles. Implementar pruebas de contrato con Pact. |
| 2024-01-08 | Logs del servicio | PR que añadió log de debug incluyó accidentalmente el campo `password` del request body | Credenciales en logs. Añadir linting de logs a CI pipeline. Agregar filtro global de campos sensibles. |
