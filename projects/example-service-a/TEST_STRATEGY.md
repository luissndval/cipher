# TEST_STRATEGY.md — auth-service
> Estrategia de pruebas del servicio de autenticación.
> Última actualización: 2024-01-15

---

## Cobertura mínima requerida

| Tipo de prueba | Cobertura mínima | Obligatoria antes de | Herramienta |
|----------------|-----------------|----------------------|-------------|
| Unitaria | 90% líneas en `src/` | Merge a cualquier rama | pytest + pytest-cov |
| Integración | Todos los endpoints críticos | Merge a main | pytest + docker-compose (test stack) |
| Contrato | Todos los consumidores de `/internal/validate` y todos los eventos emitidos | Cambio de API o schema de evento | Pact (Python) |
| E2E | Flujos: registro→verificación→login→refresh→logout | Release a producción | pytest + requests (contra staging) |
| Regresión de seguridad | Suite `tests/security/` completa verde | Cualquier cambio en plano de credenciales o tokens | pytest |

---

## Comandos de prueba

```bash
# Pruebas unitarias con cobertura
pytest tests/unit/ -v --cov=src --cov-report=term-missing --cov-fail-under=90

# Pruebas unitarias específicas de componentes críticos
pytest tests/unit/test_jwt_service.py -v         # JWT emission & validation
pytest tests/unit/test_password_service.py -v    # bcrypt hash & verify
pytest tests/unit/test_refresh_service.py -v     # token rotation & revocation
pytest tests/unit/test_rate_limiter.py -v        # rate limiting logic

# Pruebas de integración (requiere docker-compose up -d en tests/docker/)
docker-compose -f tests/docker/docker-compose.test.yml up -d
pytest tests/integration/ -v --timeout=60
docker-compose -f tests/docker/docker-compose.test.yml down

# Pruebas de integración específicas por flujo
pytest tests/integration/test_registration_flow.py -v
pytest tests/integration/test_login_flow.py -v
pytest tests/integration/test_oauth_flows.py -v
pytest tests/integration/test_password_reset.py -v
pytest tests/integration/test_session_management.py -v
pytest tests/integration/test_validate_endpoint.py -v  # CRÍTICO

# Pruebas de contrato (Pact)
# Verificar que auth-service cumple los contratos con sus consumidores
pact-verifier \
  --provider-base-url=http://localhost:8080 \
  --pact-broker-url=${PACT_BROKER_URL} \
  --provider=auth-service

# Pruebas de seguridad
pytest tests/security/ -v

# Pruebas E2E (contra staging — requiere STAGING_BASE_URL)
ENVIRONMENT=staging pytest tests/e2e/ -v -m "smoke or critical"

# Suite completa local
make test-all
# Equivalente a:
# docker-compose -f tests/docker/docker-compose.test.yml up -d && \
# pytest tests/ -v --cov=src --cov-report=html && \
# docker-compose -f tests/docker/docker-compose.test.yml down
```

---

## Criterios mínimos antes de dar por terminada una tarea

- [ ] `pytest tests/unit/` pasa al 100% (0 failures, 0 errors)
- [ ] Cobertura total en `src/` no bajó del 90%
- [ ] `pytest tests/integration/test_validate_endpoint.py` pasa (endpoint crítico de toda la plataforma)
- [ ] `pytest tests/integration/test_login_flow.py` pasa (flujo crítico de usuario)
- [ ] Si se modificó `src/tokens/` o `src/auth/`: `pytest tests/security/` pasa al 100%
- [ ] Si se modificó logging o serialización: `grep -r "password\|token_value" src/ --include="*.py" | grep "log\."` retorna vacío
- [ ] Si se modificó la API o eventos: pruebas de contrato Pact pasan
- [ ] El health check responde 200: `curl -f http://localhost:8080/health`

---

## Ambientes de prueba

| Ambiente | URL / Conexión | Cuándo usarlo | Datos de prueba |
|----------|----------------|---------------|-----------------|
| Local | `http://localhost:8080` | Desarrollo, pruebas unitarias e integración | Fixtures en `tests/fixtures/`; seed con `make seed-test-db` |
| CI (GitHub Actions) | Automático en PR | Pruebas unitarias + integración en cada PR | Mismos fixtures; DB en contenedor efímero |
| Staging | `https://auth.staging.example.com` | Pruebas E2E, regresión, contrato | Usuarios de prueba en `tests/e2e/test_users.json` — NO son cuentas reales |
| Production | `https://auth.example.com` | NUNCA ejecutar pruebas | — |

---

## Pruebas críticas (no omitir bajo ninguna circunstancia)

1. **`test_password_never_stored_plaintext`** — `tests/security/test_password_security.py::test_password_never_stored_plaintext` — Verifica INV-003: después de registrar un usuario, `password_hash` en DB no es igual a la contraseña enviada y tiene el prefijo bcrypt `$2b$`.

2. **`test_jwt_expiry_enforced`** — `tests/security/test_jwt_security.py::test_jwt_expiry_enforced` — Verifica BR-001: tokens con `exp` en el pasado son rechazados por `/internal/validate` con 401.

3. **`test_refresh_token_rotation_detects_reuse`** — `tests/security/test_refresh_rotation.py::test_refresh_token_rotation_detects_reuse` — Verifica BR-002: usar un refresh token ya usado (rotado) invalida toda la familia de tokens y retorna 401.

4. **`test_rate_limit_blocks_brute_force`** — `tests/integration/test_rate_limiting.py::test_rate_limit_blocks_brute_force` — Verifica BR-005: después de 10 intentos fallidos desde la misma IP en 5 minutos, el 11° intento retorna 429.

5. **`test_deleted_user_token_rejected`** — `tests/security/test_user_lifecycle.py::test_deleted_user_token_rejected` — Verifica INV-005: tokens de usuarios con `status=DELETED` son rechazados por `/internal/validate`.

6. **`test_validate_endpoint_latency`** — `tests/performance/test_validate_latency.py::test_validate_endpoint_latency` — Verifica que el p99 de `/internal/validate` es < 10ms en el ambiente de prueba de integración.

---

## Datos de prueba y fixtures

| Dataset | Ubicación | Descripción |
|---------|-----------|-------------|
| Usuarios base | `tests/fixtures/users.json` | 10 usuarios de prueba en varios estados (ACTIVE, PENDING_VERIFICATION, LOCKED, DELETED) |
| Tokens de prueba | `tests/fixtures/tokens.py` | Funciones para generar JWTs de prueba con parámetros controlados (expirado, con claims custom, etc.) |
| Refresh tokens | `tests/fixtures/refresh_tokens.json` | Tokens en estados ACTIVE, USED, REVOKED para probar lógica de rotación |
| Contraseñas de prueba | `tests/fixtures/passwords.py` | Contraseñas que cumplen/no cumplen la política, para probar validación de BR-003 |

**Advertencia:** Los fixtures de `users.json` contienen hashes bcrypt pre-calculados para velocidad en tests. Si el cost factor de bcrypt cambia (BR-004), los fixtures deben regenerarse con `make regenerate-fixtures`. Los fixtures NO contienen contraseñas reales — todas son strings de prueba como `TestP@ssw0rd!` que no deben usarse en ningún ambiente real.
