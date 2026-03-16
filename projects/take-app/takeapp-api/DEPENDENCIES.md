# DEPENDENCIES — takeapp-api

## Runtime
- Python: 3.12 (imagen base `python:3.12-slim`)

## Dependencias principales
| Paquete | Versión | Propósito |
|---------|---------|-----------|
| fastapi | 0.115.6 | Framework web async — router, dependencias, validación |
| uvicorn[standard] | 0.32.1 | Servidor ASGI con soporte WebSockets |
| sqlalchemy[asyncio] | 2.0.36 | ORM async con soporte PostgreSQL |
| asyncpg | 0.30.0 | Driver async para PostgreSQL (backend de SQLAlchemy) |
| alembic | 1.14.0 | Migraciones de base de datos |
| psycopg2-binary | 2.9.10 | Driver sync para PostgreSQL (usado por Alembic en scripts) |
| pydantic-settings | 2.7.0 | Configuración tipada desde variables de entorno |
| redis | 5.2.1 | Cliente Redis async — sesiones, cache, pub/sub WebSocket |
| httpx | 0.28.1 | Cliente HTTP async — llamadas a Cabify, Uber Direct, MercadoPago |
| python-jose[cryptography] | 3.3.0 | Generación y validación de JWT (access/refresh tokens) |
| passlib[bcrypt] | 1.7.4 | Hash de contraseñas (con bcrypt como backend) |
| bcrypt | 3.2.2 | Fijado a 3.2.2 — passlib 1.7.4 incompatible con ≥ 4.0 |
| python-multipart | 0.0.20 | Soporte para `OAuth2PasswordRequestForm` (form data en login) |
| email-validator | 2.2.0 | Validación de campos `EmailStr` en Pydantic |
| jinja2 | 3.1.4 | Templates HTML para emails transaccionales |
| mercadopago | 2.2.3 | SDK oficial de MercadoPago — Checkout Pro + Webhooks |

## Infraestructura
- PostgreSQL: 16 — base de datos principal (async vía asyncpg)
- Redis: 7 — almacenamiento de tokens de refresh, pub/sub para WebSockets en tiempo real

## Integraciones externas (sin SDK dedicado)
| Integración | Paquete usado | Propósito |
|-------------|---------------|-----------|
| Cabify | httpx | Despacho de pedidos + webhook de estado (`cabify.py`) |
| Uber Direct | httpx | Logística alternativa — fallback chain en `logistics.py` |
| SMTP (configurable) | smtplib + jinja2 | Envío de emails transaccionales — config guardada en DB |
| SMS | httpx | Notificaciones SMS (`sms.py`) |

## Dev / tooling
| Herramienta | Versión | Para qué |
|-------------|---------|----------|
| pytest | 8.3.4 | Framework de testing |
| pytest-asyncio | 0.24.0 | Soporte para tests async (`asyncio_mode = "auto"`) |
| anyio | 4.7.0 | Backend async compatible con pytest-asyncio |
