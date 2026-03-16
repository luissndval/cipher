# TECHNICAL_STATE — takeapp-web

## Arquitectura
Monorepo con dos aplicaciones Next.js independientes (`apps/storefront` y `apps/backoffice`), cada una con su propio `package.json` y `node_modules`. Sin `root package.json` — no hay workspace manager (Turborepo/nx). Las apps se construyen y despliegan como imágenes Docker separadas. El Dockerfile multi-stage maneja ambas apps en un solo archivo.

- **Storefront** (puerto 3000): menú público multi-tenant + checkout + tracking de pedidos. Output `standalone` para producción.
- **Backoffice** (puerto 3001): panel de administración para tenants + panel superadmin. Sin `output: standalone` configurado aún.

Routing multi-tenant en storefront via `middleware.ts` que lee el header `X-Tenant-Slug` inyectado por nginx y reescribe `/` → `/{slug}`. El backoffice usa `basePath: "/admin"`.

## Patrones identificados
- **App Router (Next.js 14)**: ambas apps usan el directorio `src/app/` con layouts, pages y route groups
- **TanStack Query**: fetching y cache de datos del servidor — separación entre server state y client state
- **Zustand**: estado global del cliente (carrito en storefront, auth en backoffice)
- **React Hook Form + Zod**: validación de formularios con schemas tipados
- **Feature flags en frontend**: `useFeatures()` + `hasFeature(key)` leen `user.features` del store — sin lógica de negocio duplicada en frontend
- **Dark mode via clase CSS**: `darkMode: 'class'` en Tailwind, anti-FOUC con script síncrono en `<head>`, remap global en `globals.css`
- **Multi-stage Docker build**: stages separados por app (deps, builder, production)

## Deuda técnica conocida
- **Zod**: storefront usa v3, backoffice usa v4 — schemas incompatibles entre apps
- **@hookform/resolvers**: versiones divergentes (v3.9 vs v5.2)
- **Next.js**: storefront en 14.2.18, backoffice en 14.2.23 — storefront desactualizado
- **output standalone**: configurado en storefront pero NO en backoffice — inconsistencia en builds de producción
- **Sin root workspace**: no hay Turborepo ni nx — no se puede correr builds/tests en paralelo ni compartir código entre apps
- **Código compartido**: tipos, utilidades y componentes potencialmente duplicados entre storefront y backoffice al no haber un paquete `packages/shared`
- **Enforcement de límites de plan**: `max_catalog_items`, `max_branches` no se validan en frontend (solo en backend)

## Testing
- Tipo: Ninguno detectado en la estructura del repo
- Cobertura estimada: desconocida — no hay carpetas `__tests__`, `*.test.ts` ni `*.spec.ts` visibles
- No hay configuración de Jest, Vitest ni Playwright en los archivos listados

## CI/CD
- **GitHub Actions** con dos workflows:
  - `sync-stage.yml`: en cada push a `main` hace merge automático de `main` → `stage`
  - `trigger-deploy.yml`: dispara el deploy en la VM GCP (self-hosted runner en TAKE-APP repo)
- El build y deploy de las imágenes Docker se orquesta desde el repo de infra (`TAKE-APP`), no desde este repo directamente
- No hay workflow de CI (lint/typecheck/tests) en este repo — el CI corre en el repo raíz
