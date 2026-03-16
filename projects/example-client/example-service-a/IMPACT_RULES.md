# IMPACT_RULES.md — auth-service
> Reglas de evaluación de impacto específicas para el servicio de autenticación.
> Última actualización: 2024-01-15

---

## Reglas de evaluación de impacto

### IR-001 — Identificar si el cambio afecta el plano de seguridad
Antes de cualquier cambio en auth-service, identificar si toca alguno de estos 4 planos:
1. **Plano de credenciales:** contraseñas, hash, policy de contraseñas
2. **Plano de tokens:** emisión, validación, rotación, expiración de JWT/refresh tokens
3. **Plano de acceso:** rate limiting, bloqueo de cuentas, OAuth flows
4. **Plano de datos de usuario:** user_id, status, email de verificación

Cualquier cambio que toque el plano de credenciales o tokens tiene nivel mínimo **CRÍTICO**.
Cualquier cambio en el plano de acceso tiene nivel mínimo **ALTO**.

### IR-002 — Evaluar impacto en el endpoint `/internal/validate`
Este endpoint es el más crítico de auth-service. Se llama en cada request autenticado de toda la plataforma.
Preguntar: ¿El cambio, directa o indirectamente, puede modificar la respuesta de `/internal/validate`?
- Si puede afectar qué tokens son aceptados/rechazados: nivel **CRÍTICO**
- Si puede afectar la latencia del endpoint en > 2ms p50: nivel **ALTO** (impacta toda la plataforma)
- Si no afecta este endpoint: continuar con evaluación normal

### IR-003 — Evaluar propagación de sesiones activas
Preguntar: ¿El cambio puede invalidar o afectar sesiones activas de usuarios en producción?
- Cambios en el secreto JWT invalidan **todas** las sesiones activas → nivel **CRÍTICO**, coordinar con todos los servicios
- Cambios en la estructura del payload JWT invalidan tokens existentes → nivel **CRÍTICO**, requiere plan de migración
- Cambios que afectan sólo nuevos tokens emitidos (no tokens existentes) → evaluar según RISK_MATRIX

### IR-004 — Verificar que no se registran datos sensibles
Todo cambio que modifique:
- Cualquier `logger.*` statement
- Serialización de objetos `User`, `RefreshToken`, o request bodies de endpoints de auth
- Código de manejo de errores (los mensajes de error pueden filtrar información)

DEBE ser revisado para garantizar que `password`, `password_hash`, `token_value`, y PII no aparecen en logs.
Correr `grep -r "password\|token_value\|secret" src/ --include="*.py" | grep "log\."` para verificar.

### IR-005 — Evaluar cambios en política de contraseñas y su retrocompatibilidad
Si el cambio endurece la política de contraseñas (BR-003):
- Las contraseñas **existentes** en DB no se ven afectadas (ya fueron hasheadas).
- Los usuarios con contraseñas que no cumplen la nueva política sólo lo notan al intentar **cambiar** su contraseña.
- Si la nueva política debe aplicarse retroactivamente: requiere forzar reset de contraseña a todos los usuarios → impacto masivo en UX → nivel **CRÍTICO** + aprobación de producto.

Si el cambio relaja la política: nivel **ALTO** (implicaciones de seguridad; aprobar con Platform Security Lead).

### IR-006 — Evaluar impacto en servicios downstream vía eventos
Revisar la tabla de eventos emitidos en DEPENDENCIES.md.
Si el cambio modifica el schema de cualquier evento emitido:
1. Identificar todos los consumidores del evento (DEPENDENCIES.md → Eventos que EMITE).
2. Verificar compatibilidad backward. Si no es compatible: coordinar deploys.
3. Ejecutar pruebas de contrato con Pact antes de desplegar.
Nivel mínimo para cambios de schema de eventos: **ALTO**.

---

## Checklist de 5 preguntas (obligatorio antes de implementar)

1. **¿Qué plano de seguridad está afectado (credenciales / tokens / acceso / datos)?** — [Respuesta]
2. **¿El cambio puede afectar `/internal/validate` o sesiones activas existentes?** — [Sí/No + cómo]
3. **¿El cambio puede resultar en logs que contengan contraseñas, tokens o PII sin enmascarar?** — [Sí/No + verificación realizada]
4. **¿Cómo se revierte si algo falla y hay usuarios afectados en producción?** — [Procedimiento con tiempo estimado]
5. **¿Qué prueba de integración o E2E confirmaría que el cambio no rompe el flujo de login/logout?** — [Test específico]

---

## Áreas de revisión por tipo de cambio en auth-service

| Tipo de cambio | Archivos a revisar siempre | Riesgo mínimo | Acción adicional |
|----------------|---------------------------|---------------|------------------|
| Cambio en JWT (claims, expiración, secreto) | BR-001, BR-002, RISK_MATRIX (componente JWT), DEPENDENCIES (consumidores de `/internal/validate`) | CRÍTICO | Coordinar con todos los servicios consumidores |
| Cambio en bcrypt / hash de contraseñas | BR-004, INV-003, RISK_MATRIX | CRÍTICO | Security review obligatorio |
| Cambio en rate limiting | BR-005, RISK_MATRIX, `src/redis/` | ALTO | Verificar que Redis fallback sigue siendo seguro |
| Cambio en flujo de registro | BR-006, DEPENDENCIES (email-service) | ALTO | Prueba E2E completa del flujo de registro |
| Cambio en OAuth | BR-006, DEPENDENCIES (Google/GitHub) | ALTO | Pruebas de contrato con el proveedor OAuth |
| Cambio en recuperación de contraseña | BR-003, RISK_MATRIX | ALTO | Verificar expiración y unicidad de tokens de reset |
| Cambio en eventos emitidos | DEPENDENCIES (sección Eventos), consumidores conocidos | ALTO | Pruebas de contrato con Pact |
| Cambio en logs | RO-002, `src/logging/` | MEDIO | Verificar con grep que no se loguean campos sensibles |
| Cambio en documentación OpenAPI | DEPENDENCIES (consumidores) | BAJO | Verificar que el spec refleja el comportamiento real |
| Refactoring de repositorio DB | INV-001, INV-004, `db/migrations/` | MEDIO | Verificar que las queries críticas siguen siendo correctas |
