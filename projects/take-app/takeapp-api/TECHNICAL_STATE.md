# TECHNICAL_STATE — takeapp-api

## Arquitectura
Monolito modular basado en FastAPI con arquitectura en capas: API (routers) → Services → Models (SQLAlchemy async). Multi-tenant via `tenant_id` en modelos. PostgreSQL como base de datos principal, Redis para sesiones/tokens. WebSocket para tracking en tiempo real. Reverse proxy Nginx gestiona routing multi-tenant por subdominio.

## Patrones identificados
- **Repository/Service Layer**: lógica de negocio encapsulada en `app/services/` (AuthService, UserService, BackofficeDashboardService, etc.)
- **Dependency Injection**: FastAPI `Depends()` para DB session, Redis, auth guards, feature flags
- **Guard/Policy pattern**: funciones `require_owner`, `require_manager`, `require_cashier`, `require_superadmin` en `deps.py` como dependencias declarativas
- **Feature flags via JSONB**: resolución dinámica `feature_overrides > plan.features` en `services/features.py`
- **Event-driven (polling)**: `poll_active_jobs()` corre cada 15s en lifespan de FastAPI para actualizar estado de delivery jobs
- **Webhook pattern**: Cabify webhook siempre retorna 200 para evitar reintentos
- **Encrypt-at-rest**: campos sensibles (MP token, Cabify API key, Google Maps key) encriptados con Fernet via `core/crypto.py`
- **Upsert seed pattern**: `seeds/plans.py` usa upsert inteligente — no pisa overrides manuales

## Deuda técnica conocida
- **Migración fantasma**: existe `208c3b613c21_add_users_table.py` sin convención de naming junto a las migraciones `001`–`020` — probablemente un artefacto de autogenerate que nunca se limpió
- **bcrypt pinneado**: `bcrypt==3.2.2` fijado por incompatibilidad con passlib 1.7.4 — deuda hasta que passlib actualice o se migre a `bcrypt` directo
- **SQL echo en development**: `echo=True` activo en development genera logs verbosos — no es deuda crítica pero añade ruido
- **`manager` role en transición**: la arquitectura evoluciona hacia `branch_admin` (Fase 10) pero `manager` aún existe en el código
- **Enforcement de límites de plan no implementado**: `max_catalog_items`, `max_branches` existen como feature flags pero no hay validación en los endpoints de creación
- **`sms.py` en integraciones**: presente pero sin uso activo documentado

## Testing
- **Tipo**: unitarios/integración con pytest-asyncio
- **Framework**: pytest 8.3.4 + pytest-asyncio 0.24.0
- **Configuración**: `asyncio_mode = "auto"` en `pyproject.toml`, fixture loop scope = "session"
- **Cobertura estimada**: baja — carpeta `tests/` existe pero no hay evidencia de cobertura configurada ni CI que la reporte
- **Comando**:
  ```bash
  pytest
  # o con verbose
  pytest -v tests/
  ```

## CI/CD
- **GitHub Actions** (self-hosted runner en VM GCP):
  - `ci.yml` (en repo TAKE-APP raíz): tests backend con pytest + type-check storefront — trigger: push a `main`/`develop`, PR a `main`
  - `sync-stage.yml`: merge automático de `main` → `stage` en cada push a `main`
  - `trigger-deploy.yml`: dispara deploy en la VM GCP (workflow_dispatch)
- **Deploy**: `git pull` en los 3 repos + `docker compose up --build -d` + alembic upgrade (opcional)
- **Runner**: self-hosted en VM Ubuntu GCP `34.46.103.1`
