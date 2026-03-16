# BUSINESS_RULES — takeapp-api

## Propósito
TakeApp es una plataforma SaaS multi-tenant para gestión de pedidos y menús digitales orientada a negocios gastronómicos y comercios (restaurantes, pastelerías, mercados). Permite a los tenants publicar su catálogo online, recibir pedidos con múltiples métodos de pago, coordinar logística de delivery y administrar su operación desde un backoffice propio.

## Usuarios / consumidores

| Rol | Descripción |
|-----|-------------|
| `superadmin` | Administrador de la plataforma — gestiona tenants, planes, configuración global |
| `owner` | Dueño del negocio — acceso total a su tenant |
| `branch_admin` | Administrador de sucursal — gestiona su sucursal (reemplaza `manager`) |
| `cashier` | Cajero — toma pedidos en mostrador dentro de su sucursal |
| `kitchen` | Cocina — visualiza y actualiza estado de pedidos en preparación |
| Clientes finales | Consumidores que acceden al storefront público para ver el menú y realizar pedidos |

## Reglas de negocio

### Autenticación y seguridad
- El login usa `OAuth2PasswordRequestForm` (form data, no JSON) — devuelve `access_token` + `refresh_token`
- Los tokens de acceso expiran según `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60 min)
- Las contraseñas se hashean con `bcrypt 3.2.2` (fijado — passlib 1.7.4 es incompatible con bcrypt ≥ 4.0)
- Datos sensibles (`mp_access_token`, `cabify_api_key`, `google_maps_api_key`) se cifran con Fernet antes de persistir en DB
- `cabify_secret_key` (webhook secret) se guarda en plaintext
- El endpoint `/me` devuelve las features resueltas del tenant en `user.features`
- Usuarios con `must_change_password = true` deben actualizar su contraseña en el primer login

### Multi-tenancy
- Cada tenant tiene un `slug` único que identifica su subdominio
- Los tenants pertenecen a un `Plan` (Starter / Pro / Scale) con features en JSONB
- Las features se resuelven por precedencia: `feature_overrides` (subscription) > `plan.features` > None
- El catálogo (categorías, productos, combos, extras) es compartido por todo el tenant
- Los pedidos, usuarios, horarios, configuración de pagos y logística son independientes por sucursal (`Branch`)

### Feature flags y planes

| Feature | Starter | Pro | Scale |
|---------|---------|-----|-------|
| `max_catalog_items` | 30 | 150 | ilimitado |
| `max_branches` | 1 | 3 | ilimitado |
| `payment_mercadopago` | ❌ | ✅ | ✅ |
| `logistics_cabify` / `logistics_uber` | ❌ | ✅ | ✅ |
| `coupons` | ❌ | ✅ | ✅ |
| `custom_domain` | ❌ | ❌ | ✅ |
| `analytics` | none | basic | full |
| `priority_support` | ❌ | ❌ | ✅ |

- El guard `require_feature("key")` como `Depends` bloquea endpoints según el plan del tenant
- El superadmin puede aplicar `feature_overrides` por tenant individualmente

### Pedidos y pagos
- Los pedidos se asocian a una `Branch` específica
- Métodos de pago disponibles: efectivo, transferencia bancaria, MercadoPago Checkout Pro
- MercadoPago opera con webhooks para confirmar pagos — el backend los valida antes de actualizar el estado del pedido
- Los estados de pedido siguen un flujo definido: `pending → confirmed → preparing → ready → delivered / cancelled`

### Logística de delivery
- Proveedores soportados: Uber Direct y Cabify (con fallback chain configurable)
- `logistics_uber_enabled` es un toggle global administrado por el superadmin desde `system_settings`
- El polling de `delivery_jobs` activos corre cada 15 segundos en el lifespan de la app
- El webhook de Cabify siempre devuelve HTTP 200 para evitar reintentos del proveedor
- La dirección local del tenant se usa como punto de origen para las cotizaciones de delivery

### Catálogo y productos
- Los `ProductOptionGroup` tienen `type`: `single` (radio), `multiple` (checkbox) o `quantity` (stepper)
- Las `ProductOption` con `is_default = true` se pre-seleccionan al abrir el modal del storefront
- El campo `product_id` en `OrderItem` es nullable (migración 010) — permite ítems sin producto catálogo
- Las imágenes de producto se almacenan como URLs; el campo es nullable y se limpia enviando `null`

### SMTP y notificaciones
- La configuración SMTP es por plataforma (no por tenant) y la gestiona el superadmin
- En `environment=development` sin SMTP configurado: los emails se loguean como `[EMAIL MOCK]` y se registran con `status="mock"`
- El sistema soporta 16 tipos de notificaciones por email con templates Jinja2

### Roles y permisos de creación de usuarios
```
owner        → puede crear: branch_admin, cashier, kitchen
branch_admin → puede crear: cashier, kitchen (solo en su propia branch)
```
- `branch_id` es `null` para `owner`, obligatorio para `branch_admin`, `cashier` y `kitchen`

### Multi-sucursal
- Si un tenant tiene más de 1 sucursal activa, el storefront muestra un selector antes del menú
- Si solo tiene 1 sucursal activa, va directo al menú sin pantalla de selección
- El alta de un nuevo tenant crea automáticamente una `Branch` inicial ("Principal") + usuario `owner`

### Configuración de plataforma (superadmin)
- `google_maps_api_key` es global — lo configura el superadmin y aplica a todos los tenants
- El endpoint público `GET /api/v1/public/platform-settings` devuelve la clave desencriptada sin autenticación (para uso en el frontend)

## Integraciones externas

| Servicio | Propósito |
|----------|-----------|
| **MercadoPago** | Checkout Pro para pagos online; webhooks para confirmación asíncrona de pagos |
| **Uber Direct** | Logística de delivery en tiempo real con tracking; toggle global vía superadmin |
| **Cabify** | Logística de delivery alternativa; webhook de estado de envíos (`/webhooks/cabify/parcel-status`) |
| **Google Maps** | Autocomplete de dirección en checkout del storefront; clave API global configurada por superadmin |
| **SMTP externo** | Envío de emails transaccionales (confirmación de pedido, reset de contraseña, bienvenida, etc.) |
| **Redis** | Gestión de sesiones/tokens, cache, pub/sub para WebSockets |
| **PostgreSQL** | Persistencia principal — schemas multi-tenant en una sola base de datos |
