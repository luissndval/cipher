# IMPACT_RULES — takeapp-web

## Zonas de alto impacto — NO modificar sin revisión

| Archivo / Módulo | Por qué es crítico |
|------------------|--------------------|
| `apps/storefront/src/middleware.ts` | Lee el header `X-Tenant-Slug` (inyectado por nginx) y reescribe `/` → `/{slug}`. Si falla, todo el routing multi-tenant del storefront se rompe |
| `apps/storefront/src/lib/api.ts` | Centraliza todos los fetches del storefront (`fetchMenu`, `createOrder`, `fetchTenantPublic`, `fetchPlatformSettings`). Cambios rompen múltiples páginas a la vez |
| `apps/storefront/src/store/cart.ts` | Zustand store persistido en localStorage. Cambios en la forma del estado pueden corromper carts de usuarios existentes |
| `apps/storefront/src/app/[tenant]/checkout/page.tsx` | Punto de conversión: integra Google Maps Autocomplete, cotización de delivery y creación de orden. Regresiones aquí impactan directamente ingresos |
| `apps/backoffice/src/hooks/useAuth.ts` | Zustand store del usuario autenticado. Fuente de verdad para rol, features resueltas y tenant slug en todo el backoffice |
| `apps/backoffice/src/types/auth.ts` | Define `TenantRole`, `PlatformRole`, `isPlatformUser()`, `hasMinRole()` y la forma de `User.features`. Cambios aquí rompen guards en toda la app |
| `apps/backoffice/src/hooks/useFeatures.ts` | `hasFeature()` y `getFeatureValue()` — usados en decenas de componentes para mostrar/ocultar funcionalidad según el plan. Cambios silenciosos pueden exponer features de pago |
| `apps/backoffice/src/app/(app)/admin/settings/platform/` | Configura Google Maps API key global y toggle de Uber Direct. Afecta a todos los tenants de la plataforma |
| `apps/backoffice/src/components/layout/Sidebar.tsx` | Nav dinámico por rol + `useBusinessLabels`. Controla qué rutas son visibles según rol — cambios pueden exponer o esconder rutas incorrectamente |
| `apps/storefront/next.config.mjs` | `output: "standalone"` — requerido para que el build de producción funcione en Docker. Eliminarlo rompe el deploy |
| `apps/backoffice/next.config.mjs` | `basePath: "/admin"` — Nginx enruta `/admin/*` a este servicio. Cambiar el basePath rompe todo el routing del panel |
| `Dockerfile` (raíz) | Multi-stage build para ambas apps. Cambios en las etapas de deps o producción afectan todos los deploys |

## Reglas

- **No cambiar `basePath: "/admin"`** en `apps/backoffice/next.config.mjs` sin actualizar simultáneamente la configuración de Nginx en el repo de infra.
- **No cambiar la forma del estado de `cart.ts`** sin escribir una migración de Zustand (`migrate` + `version`) para no corromper el localStorage de usuarios activos.
- **No agregar/renombrar roles** en `apps/backoffice/src/types/auth.ts` sin actualizar `hasMinRole()`, los guards del backend (`api/deps.py`) y los seeds simultáneamente.
- **No quitar `output: "standalone"`** del `next.config.mjs` del storefront — es requerido por el Dockerfile de producción.
- **No cambiar la firma de `fetchPlatformSettings()` ni `fetchTenantPublic()`** sin auditar todos los componentes que las consumen (checkout, BranchSelector, etc.).
- **Cualquier cambio en `middleware.ts` del storefront** debe probarse con todos los slugs de tenant registrados y con el header `X-Tenant-Slug` presente/ausente.
- **Los feature flags** (`hasFeature`) son la única barrera de acceso a funcionalidades de pago desde el frontend — cualquier cambio en `useFeatures.ts` requiere revisión de seguridad.
