# DEPENDENCIES — takeapp-web

## Runtime
- Node.js: 20 (Alpine)
- TypeScript: ^5

## Apps del monorepo

Monorepo sin root `package.json`. Cada app tiene su propio `package.json` y `node_modules` independientes.

---

## Storefront (`apps/storefront/`) — Next.js 14.2.18

### Dependencias principales

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| `next` | 14.2.18 | Framework React (App Router, output: standalone) |
| `react` / `react-dom` | ^18.3.1 | UI base |
| `axios` | ^1.7.9 | Cliente HTTP para llamadas al backend |
| `zustand` | ^5.0.2 | Estado global del carrito (persistido en localStorage) |
| `@tanstack/react-query` | ^5.62.7 | Fetching y caché de datos servidor |
| `@tanstack/react-query-devtools` | ^5.62.7 | Devtools para TanStack Query |
| `react-hook-form` | ^7.54.2 | Manejo de formularios |
| `@hookform/resolvers` | ^3.9.1 | Integración RHF + Zod |
| `zod` | ^3.23.8 | Validación de esquemas |
| `@radix-ui/react-dialog` | ^1.1.15 | Modal (ProductOptionsModal, etc.) |
| `@radix-ui/react-label` | ^2.1.8 | Labels accesibles |
| `@radix-ui/react-radio-group` | ^1.3.8 | Selector de método de pago |
| `@radix-ui/react-slot` | ^1.2.4 | Componente polimórfico Radix |
| `@mercadopago/sdk-js` | ^0.0.3 | MercadoPago JS SDK (checkout) |
| `@mercadopago/sdk-react` | ^1.0.7 | MercadoPago componentes React |
| `@react-google-maps/api` | ^2.20.8 | Google Maps Autocomplete (dirección delivery) |
| `leaflet` | ^1.9.4 | Mapa de tracking del repartidor |
| `react-leaflet` | ^4.2.1 | Wrapper React para Leaflet |
| `lucide-react` | ^0.575.0 | Iconos SVG |
| `motion` | ^12.34.3 | Animaciones (Framer Motion v12) |
| `sonner` | ^2.0.7 | Toast notifications |
| `date-fns` | ^3.6.0 | Formateo de fechas |
| `class-variance-authority` | ^0.7.1 | Variantes de clases CSS (CVA) |
| `tailwind-merge` | ^3.5.0 | Merge de clases Tailwind sin conflictos |
| `@tailwindcss/container-queries` | ^0.1.1 | Plugin Tailwind container queries |

### Dev / tooling (storefront)

| Herramienta | Versión | Propósito |
|-------------|---------|-----------|
| `tailwindcss` | ^3.4.17 | Framework CSS utilitario |
| `autoprefixer` | ^10.4.20 | PostCSS autoprefixer |
| `postcss` | ^8.4.49 | Procesador CSS |
| `typescript` | ^5 | Tipado estático |
| `@types/leaflet` | ^1.9.16 | Tipos para Leaflet |
| `@types/node` | ^20 | Tipos Node.js |
| `@types/react` | ^18 | Tipos React |

---

## Backoffice (`apps/backoffice/`) — Next.js 14.2.23

### Dependencias principales

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| `next` | 14.2.23 | Framework React (App Router, basePath: /admin) |
| `react` / `react-dom` | ^18 | UI base |
| `axios` | ^1.13.5 | Cliente HTTP para llamadas al backend |
| `zustand` | ^5.0.11 | Estado global de auth y UI |
| `@tanstack/react-query` | ^5.90.21 | Fetching y caché de datos servidor |
| `react-hook-form` | ^7.71.2 | Manejo de formularios |
| `@hookform/resolvers` | ^5.2.2 | Integración RHF + Zod |
| `zod` | ^4.3.6 | Validación de esquemas (v4 — distinto a storefront) |
| `@radix-ui/react-dialog` | ^1.1.15 | Modales |
| `@radix-ui/react-label` | ^2.1.8 | Labels accesibles |
| `@radix-ui/react-popover` | ^1.1.15 | Popover (date pickers, etc.) |
| `@radix-ui/react-select` | ^2.2.6 | Selector accesible (con Controller RHF) |
| `@radix-ui/react-slot` | ^1.2.4 | Componente polimórfico Radix |
| `@radix-ui/react-switch` | ^1.2.6 | Toggle switches (con Controller RHF) |
| `@react-google-maps/api` | ^2.20.8 | Google Maps Autocomplete (dirección branch) |
| `leaflet` | ^1.9.4 | Mapa en BranchMapView / DriverMap |
| `react-leaflet` | ^4.2.1 | Wrapper React para Leaflet |
| `recharts` | ^2.15.4 | Gráficas del dashboard y estadísticas |
| `lucide-react` | ^0.575.0 | Iconos SVG |
| `date-fns` | ^4.1.0 | Formateo de fechas |
| `clsx` | ^2.1.1 | Utilidad para clases condicionales |
| `class-variance-authority` | ^0.7.1 | Variantes de clases CSS (CVA) |
| `tailwind-merge` | ^3.5.0 | Merge de clases Tailwind sin conflictos |
| `@tailwindcss/container-queries` | ^0.1.1 | Plugin Tailwind container queries |

### Dev / tooling (backoffice)

| Herramienta | Versión | Propósito |
|-------------|---------|-----------|
| `tailwindcss` | ^3.4.1 | Framework CSS utilitario |
| `postcss` | ^8 | Procesador CSS |
| `typescript` | ^5 | Tipado estático |
| `eslint` | ^8 | Linting |
| `eslint-config-next` | 14.2.23 | Reglas ESLint para Next.js |
| `@types/leaflet` | ^1.9.16 | Tipos para Leaflet |
| `@types/node` | ^20 | Tipos Node.js |
| `@types/react` | ^18 | Tipos React |

---

## Infraestructura

- **PostgreSQL**: 16 — base de datos principal (consumida vía backend)
- **Redis**: 7 — caché y pub/sub WebSocket (consumido vía backend)
- **Docker**: multi-stage build (`deps-*` → `builder-*` → `production-*`)
- **Nginx**: reverse proxy — inyecta `X-Tenant-Slug` header para multi-tenancy

---

## Inconsistencias entre apps (deuda técnica)

| Paquete | Storefront | Backoffice | Impacto |
|---------|-----------|------------|---------|
| `zod` | ^3.23.8 | ^4.3.6 | API diferente entre v3 y v4 |
| `@hookform/resolvers` | ^3.9.1 | ^5.2.2 | Firma de `zodResolver` cambia |
| `next` | 14.2.18 | 14.2.23 | Storefront desactualizado |
| `date-fns` | ^3.6.0 | ^4.1.0 | API mayor diferente |
| `@tanstack/react-query` | ^5.62.7 | ^5.90.21 | Menor — mismo major |
