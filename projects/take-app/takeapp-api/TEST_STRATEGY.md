# TEST_STRATEGY — takeapp-api

## Frameworks
- **pytest 8.3.4**: framework principal de testing
- **pytest-asyncio 0.24.0**: soporte para tests asíncronos (asyncio_mode = "auto")
- **anyio 4.7.0**: compatibilidad async multi-backend

## Comandos
```bash
# Correr todos los tests
pytest

# Correr con output detallado
pytest -v

# Correr un archivo específico
pytest tests/test_auth.py

# Correr con cobertura (si pytest-cov está instalado)
pytest --cov=app tests/
```

## Configuración (pyproject.toml)
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
testpaths = ["tests"]
```

## Qué se prueba
- **Auth**: login, tokens, validaciones de rol — inferido de la estructura de `app/api/v1/auth.py`
- **Endpoints backoffice**: dashboard, métricas, pedidos — inferido de `app/api/v1/backoffice/`
- **Servicios**: lógica de negocio en `app/services/` (features, logistics, auth)

## Qué NO se prueba (gaps identificados)
- **Tests de integración real**: no hay docker-compose de test — los tests probablemente mockean la DB o usan SQLite en memoria
- **Tests e2e**: no detectados — no hay Playwright, Cypress ni similar
- **Cobertura mínima**: no hay umbral de cobertura configurado (`--cov-fail-under`)
- **Tests de webhooks**: `integrations/cabify.py`, `integrations/mercadopago.py` — cobertura incierta
- **Tests de email**: comportamiento del mock SMTP (`[EMAIL MOCK]`) no verificado formalmente
- **Tests de migraciones Alembic**: no detectados scripts de validación de schema
- **Cobertura de modelos**: 20+ modelos en `app/models/` — cobertura estimada baja

## Cobertura estimada
- **Global**: baja-media — carpeta `tests/` existe pero no hay evidencia de tests exhaustivos en el árbol proporcionado
- **Área mejor cubierta**: auth y endpoints principales (rutas críticas del backoffice)
- **Área menos cubierta**: integraciones externas (Cabify, Uber, MercadoPago), seeds, migraciones
