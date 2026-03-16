# TASK_FLOW.md — auth-service
> Flujo de trabajo para tareas de modificación en el servicio de autenticación.
> Última actualización: 2024-01-15

---

## Pasos obligatorios (en orden)

### Paso 1 — Leer contexto activo de auth-service
Verificar que `.claude/ACTIVE_CONTEXT.md` contiene el contexto de `example-service-a` (auth-service).
Si no: ejecutar `bash brain-agent/scripts/detect-context.sh`.
Confirmar que las BUSINESS_RULES, RISK_MATRIX y DEPENDENCIES de auth-service están cargadas.
**Salida esperada:** Confirmación explícita: "Contexto de auth-service cargado. Reglas críticas: BR-001 (JWT 15min), BR-002 (token rotation), BR-004 (bcrypt cost 12)."

---

### Paso 2 — Describir el cambio con perspectiva de seguridad
Reformular el cambio incluyendo:
- Qué componente de seguridad se modifica (plano de credenciales / tokens / acceso / datos)
- Qué invariante podría verse afectado (revisar INV-001 a INV-005)
- Si hay usuarios activos que podrían verse afectados en el momento del deploy
**Salida esperada:** Descripción que incluye el plano de seguridad afectado y los invariantes relevantes.

---

### Paso 3 — Identificar archivos con énfasis en archivos de seguridad
Listar archivos afectados y adicionalmente verificar:
- Si el cambio está en `src/tokens/`: revisar `tests/unit/test_jwt_service.py` y `tests/integration/test_validate_endpoint.py`
- Si el cambio está en `src/auth/`: revisar `tests/unit/test_password_service.py`
- Si el cambio está en `src/api/v1/`: revisar el spec OpenAPI (`docs/api/openapi.yaml`)
- Si el cambio modifica modelos DB: revisar `db/migrations/` y el schema actual
**Salida esperada:** Lista de archivos con rol claramente asignado (modificar / referencia / no tocar).

---

### Paso 4 — Aplicar IMPACT_RULES.md de auth-service
Responder las 5 preguntas del checklist de IMPACT_RULES.md.
**Énfasis especial:**
- IR-001: ¿Qué plano de seguridad? → Determina nivel mínimo de riesgo
- IR-002: ¿Afecta `/internal/validate`? → Si sí: coordinar con todos los servicios antes de continuar
- IR-003: ¿Afecta sesiones activas existentes? → Si sí: calcular impacto en usuarios actuales
- IR-004: ¿Algún log nuevo puede contener datos sensibles?
**Salida esperada:** Nivel de riesgo determinado con justificación por cada IR aplicable.

---

### Paso 5 — Revisar DEPENDENCIES.md de auth-service
Verificar:
1. Si el cambio toca la interfaz de `/internal/validate`: notificar a todos los servicios listados en "Dependencias de entrada"
2. Si el cambio toca eventos emitidos: verificar consumidores y ejecutar pruebas de contrato
3. Si el cambio toca la integración con Redis: verificar que la lógica de fallback sigue siendo correcta (ver advertencia crítica #1)
4. Si el cambio toca el campo `password_hash`: verificar que no aparece en ningún serializer (ver advertencia crítica #2)
**Salida esperada:** "Sin impacto en dependencias externas" O lista específica de dependencias a coordinar.

---

### Paso 6 — Consultar RISK_MATRIX.md de auth-service
Identificar el componente exacto en la matriz y su nivel.
Si el nivel es CRÍTICO:
- Preparar el procedimiento de rollback específico (incluyendo si requiere rotación de secreto JWT)
- Identificar si hay usuarios activos que necesitan ser notificados
- Confirmar que el Platform Security Lead está disponible para revisar
Si el nivel es ALTO:
- Confirmar que el tech lead está en el loop
- Verificar que el ambiente de staging está disponible para pruebas de integración
**Salida esperada:** Nivel confirmado, procedimiento de rollback preparado, stakeholders identificados.

---

### Paso 7 — Propuesta de cambio con formato de AGENT.md
Incluir en la propuesta, además del formato estándar:
- Plano de seguridad afectado
- Invariantes que se verificaron (de INV-001 a INV-005)
- Comando específico de prueba que confirma que no hay regresión de seguridad
- Plan de rollback (especialmente si hay riesgo de sesiones activas afectadas)
Esperar confirmación explícita, especialmente si el nivel es CRÍTICO o ALTO.
**Salida esperada:** Aprobación del usuario con acknowledgment del nivel de riesgo.

---

### Paso 8 — Implementar, verificar y reportar
Implementar sólo lo declarado. Al finalizar:
1. Ejecutar `pytest tests/unit/ -v` — deben pasar al 100%
2. Ejecutar `pytest tests/integration/test_auth_flows.py -v` — especialmente:
   - `test_login_flow_complete`
   - `test_refresh_token_rotation`
   - `test_invalid_token_rejected`
3. Si se modificó logging: ejecutar `grep -r "password\|token_value\|secret" src/ --include="*.py" | grep "log\."` — resultado debe ser vacío
4. Verificar que el health check del servicio pasa: `curl http://localhost:8080/health`
**Salida esperada:** Reporte con: tests ejecutados, tests que pasaron, resultado del grep de logs, estado del health check.

---

## Casos especiales en auth-service

### Cambio urgente por vulnerabilidad de seguridad
1. Si se detecta una vulnerabilidad activa, el flujo normal puede acortarse PERO nunca saltarse.
2. Notificar INMEDIATAMENTE al Platform Security Lead (no esperar a implementar).
3. Evaluar si la vulnerabilidad requiere acción inmediata en producción (patch de emergencia) o puede esperar al próximo deploy.
4. Documentar el CVE o descripción técnica de la vulnerabilidad en el commit.
5. Post-mortem en 48 horas es obligatorio.

### Cambio en duración de tokens (BR-001)
Este es un cambio con impacto en toda la plataforma. Adicionalmente al flujo normal:
1. Calcular el impacto en UX (más expiración = más re-logins forzados).
2. Coordinar con el equipo de frontend y mobile antes de cambiar.
3. Desplegar con feature flag si es posible para poder revertir sin downtime.

### Migración de schema de DB
Las migraciones de la tabla `users` o `refresh_tokens` requieren:
1. Identificar todos los servicios con FK o queries directas a estas tablas.
2. Diseñar migración como backward-compatible (añadir columna antes de remover la antigua).
3. Coordinar el orden de deploys con los servicios dependientes.
4. Tener script de rollback de la migración preparado y probado ANTES de ejecutar en producción.
