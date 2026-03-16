# BUSINESS_RULES — takeapp-web

## Propósito
TakeApp Web es el frontend de una plataforma SaaS multi-tenant para comercios gastronómicos y mercados. Provee dos aplicaciones: un **storefront** (tienda pública por tenant) donde los clientes navegan el menú, configuran productos y realizan pedidos con distintos métodos de pago; y un **backoffice** (panel administrativo) donde operadores y superadmins gestionan menú, pedidos, usuarios, integraciones y configuración de la plataforma.

## Usuarios / consumidores

| Usuario | App | Descripción |
|---|---|---|
| Cliente final | Storefront | Navega el menú, agrega productos al carrito, hace checkout y sigue el estado de su pedido |
| Owner | Backoffice | Acceso total al tenant: menú, pedidos, usuarios, configuración completa |
| Manager | Backoffice | Acceso a menú, pedidos y configuración; no puede gestionar usuarios |
| Cashier | Backoffice | Toma pedidos en mostrador; acceso limitado a dashboard y órdenes |
| Kitchen | Backoffice | Vista de cocina/preparación; solo ve dashboard, órdenes y kitchen view |
| Superadmin | Backoffice | Gestiona tenants, planes, estadísticas, SMTP y configuraciones globales de plataforma |
| Commercial | Backoffice | Rol de plataforma — solo accede a "Mis Tenants", bloqueado de planes/stats/settings |

## Reglas de negocio

### Carrito y productos
- Todo producto abre `ProductOptionsModal` (con o sin variantes) — cantidad y notas siempre disponibles
- `ProductOptionGroup` tiene tipo `single | multiple | quantity` con `min_options`, `max_options` y `is_required`
- Opciones con `is_default = true` se preseleccionan al abrir el modal
- Para grupos de tipo `quantity`, el stepper es por opción individual (independiente de `itemQty` global)
- El precio del botón de confirmación = `(precio_base + extras) × itemQty`
- Al disminuir cantidad a ≤ 0, el ítem se elimina automáticamente del carrito
- El carrito se persiste en `localStorage` bajo la clave `"takeapp-cart"` (Zustand persist)

### Checkout y pedidos
- Tipo de pedido obligatorio: `takeaway | delivery`
- Método de pago obligatorio: `mercadopago | transfer | cash`
- Para delivery: la dirección debe tener ≥ 5 caracteres (validación Zod en frontend)
- Para delivery: el pago en efectivo (`cash`) está excluido — no se muestra como opción
- MercadoPago solo está disponible si el superadmin lo tiene habilitado globalmente **y** el tenant lo activa
- Al menos 1 método de pago debe estar habilitado; si no, el panel de settings muestra advertencia y los clientes no pueden completar pedidos
- Si el pago falla (MercadoPago), el carrito se restaura desde caché pendiente si tienen <30 min de antigüedad (TTL)
- El cupón se valida contra el backend (`POST /orders/validate-coupon`) antes de crear el pedido; se aplica el `discount_amount` retornado

### Tracking de pedidos
- Si el estado del pedido es `failed`, el frontend restaura automáticamente el carrito pendiente (si existe y es válido)
- Si el estado no es `failed`, se limpian tanto el carrito activo como el pendiente
- El flujo de transferencia muestra CBU/alias y permite subir comprobante

### Roles y permisos
- Jerarquía de roles tenant: `kitchen < cashier < manager < owner`
- Kitchen: solo Dashboard + Orders + Kitchen view
- Cashier: Dashboard + Orders + Kitchen
- Manager: todo excepto gestión de usuarios
- Owner: acceso total al tenant
- Superadmin/Commercial son roles de plataforma (`platform_role`), no de tenant
- Commercial está bloqueado de `/admin/plans`, `/admin/stats`, `/admin/settings/*`
- `manager` está en proceso de ser reemplazado por `branch_admin` (Fase 10)

### Feature flags y planes
- Los features se resuelven en el backend: `feature_overrides > plan.features`
- `/me` devuelve el objeto `features` resuelto; el frontend lee de `user.features` (store Zustand)
- `hasFeature(key)` retorna `false` si el valor es `undefined | null | false | "none"`
- Si un feature no está disponible, se muestra `<UpgradeBanner feature="..." requiredPlan="..." />` en lugar de la sección

### Configuraciones de plataforma (superadmin)
- **Google Maps API Key**: única y compartida para todos los tenants, almacenada encriptada en `system_settings`; se usa para autocomplete de direcciones en logística
- **Uber Direct (toggle global)**: si se desactiva, ningún tenant puede usar Uber; Cabify funciona como fallback si está configurado
- **Cabify (toggle global)**: si se desactiva, fallback a Uber o despacho manual
- **MercadoPago (toggle global)**: si está desactivado, ningún tenant puede activarlo ni ningún cliente puede seleccionarlo; el storefront oculta la opción completamente

### Configuraciones por tenant
- Cada tenant puede activar/desactivar: MercadoPago (si habilitado globalmente), transferencia, efectivo
- Configuración de logística (Uber Direct + Cabify) requiere credenciales propias del tenant más la dirección de retiro local
- La dirección de retiro es compartida entre Uber y Cabify dentro del mismo tenant
- `PATCH` en configuraciones usa `model_dump(exclude_unset=True)` — permite enviar `null` para limpiar campos nullable

### Multi-tenant (storefront)
- El middleware lee el header `X-Tenant-Slug` (inyectado por Nginx) y reescribe `/` → `/{slug}/`
- No parsea el `Host` directamente; depende de Nginx para la resolución del tenant
- Si el tenant tiene más de 1 sucursal activa, el storefront muestra selector de sucursales antes del menú
- Si solo tiene 1 sucursal activa, va directo al menú sin pantalla intermedia

### Labels dinámicos por `business_type`
- `restaurant` → "Menú", "Cocina", "En preparación", "Listo"
- `market` → "Catálogo", "Preparación", "Armando pedido", "Listo para despacho"
- Afecta sidebar, vistas de órdenes y kitchen; se obtiene de `/api/v1/backoffice/settings/appearance`

## Integraciones externas

| Servicio | App | Uso |
|---|---|---|
| **MercadoPago** | Storefront | Checkout Pro — redirige a `init_point` (prod) o `sandbox_init_point` (local); recuperación de carrito post-pago |
| **Uber Direct** | Storefront + Backoffice | Cotización de delivery en checkout; tracking de conductor en tiempo real vía WebSocket |
| **Cabify** | Storefront + Backoffice | Cotización y despacho; tracking URL en tiempo real; webhook de estado de paquete |
| **Google Maps** | Storefront + Backoffice | Autocomplete de dirección en checkout y configuración de logística; API Key global configurada por superadmin |
| **Backend API (FastAPI)** | Ambas | Todos los datos: menú, pedidos, usuarios, settings, webhooks, WebSocket tracking |
