# IMPACT_RULES — takeapp-api

## Zonas de alto impacto — NO modificar sin revisión

| Archivo / Módulo | Por qué es crítico |
|------------------|--------------------|
| `app/core/config.py` | Settings globales con pydantic-settings — SECRET_KEY, DATABASE_URL, FERNET_KEY. Cambios rompen toda la app. |
| `app/core/crypto.py` | `encrypt_str()` / `decrypt_str()` con Fernet — usado para MP tokens, Cabify API key, Google Maps key. Cambiar la lógica corrompe datos encriptados en DB. |
| `app/core/database.py` | Engine async SQLAlchemy + `get_db()`. Cualquier cambio afecta todas las rutas con acceso a DB. |
| `app/api/deps.py` | Guards de autenticación y autorización (`require_owner`, `require_superadmin`, etc.). Un error aquí expone endpoints a usuarios no autorizados. |
| `app/api/v1/auth.py` | Login (OAuth2PasswordRequestForm), `/me`, refresh, reset password. Núcleo de autenticación — cualquier regresión afecta a todos los usuarios. |
| `app/services/auth/` | Paquete de autenticación (`AuthService`, `token_service.py`). **Es paquete, no módulo** — no crear `auth.py` al mismo nivel (shadow). |
| `app/services/features.py` | `get_feature()`, `require_feature()` — resolución de feature flags. Afecta qué endpoints son accesibles según el plan del tenant. |
| `alembic/versions/` | Migraciones de DB (001→020). Las migraciones aplicadas en prod son **irreversibles en la práctica**. Nunca editar una migración ya deployada. |
| `app/seeds/plans.py` | Seed de planes Starter/Pro/Scale con features JSONB. Un error puede sobreescribir features de producción. |
| `app/models/user.py` | Modelo User con `TenantRole` y `PlatformRole`. Cambios en roles o campos afectan auth, guards y todos los endpoints. |
| `app/models/order.py` | Modelo Order + `OrderStatus`. Central para pedidos, pagos, logística y dashboard. |
| `app/integrations/mercadopago.py` | Integración de pagos real. Errores aquí afectan cobros y webhooks de MercadoPago. |
| `app/integrations/cabify.py` | Integración de logística real. Errores afectan dispatch de pedidos y webhooks de Cabify. |
| `app/integrations/uber_flash.py` | Integración Uber Direct real. Controlada por `logistics_uber_enabled` en system_settings. |
| `app/services/logistics.py` | `dispatch_order()` y `poll_active_jobs()` — fallback chain Uber→Cabify. Lee settings globales antes de intentar Uber. |
| `app/services/system_settings.py` | `get_platform_config/save_platform_config`, `get_smtp_config/save_smtp_config`. Configuración global de la plataforma. |
| `app/api/v1/webhooks/cabify.py` | **Siempre debe devolver 200** — si no, Cabify reintenta el webhook indefinidamente. |

## Reglas

- **Nunca editar migraciones Alembic ya aplicadas** — crear una nueva migración para corregir el schema.
- **No crear `services/auth.py`** — el paquete `services/auth/` quedaría sombreado y el import fallaría silenciosamente.
- **`bcrypt` fijado a `3.2.2`** — passlib 1.7.4 es incompatible con bcrypt ≥ 4.0. No actualizar bcrypt sin validar compatibilidad.
- **PATCH endpoints deben usar `model_dump(exclude_unset=True)`**, no `exclude_none=True` — permite enviar `null` para limpiar campos nullable.
- **Login usa `OAuth2PasswordRequestForm` (form data)**, no JSON — no cambiar el content-type sin actualizar todos los clientes.
- **Webhook Cabify debe retornar siempre HTTP 200** — incluso en errores internos — para evitar reintentos infinitos.
- **Campos encriptados en DB** (`cabify_api_key`, `mp_access_token`, `google_maps_api_key`) deben pasar siempre por `encrypt_str()`/`decrypt_str()` — nunca guardar en plaintext.
- **`require_feature()`** debe usarse como `Depends` en todos los endpoints que correspondan a features de plan — no hacer la verificación manualmente inline.
- **Polling de delivery_jobs** corre cada 15s en el lifespan de FastAPI — cambios en `logistics.py` pueden afectar jobs activos en vuelo.
