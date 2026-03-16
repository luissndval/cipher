# RISK_MATRIX — takeapp-web

| Riesgo | Severidad | Probabilidad | Mitigación |
|--------|-----------|--------------|------------|
| Dos versiones de Next.js activas (storefront 14.2.18 vs backoffice 14.2.23) | Media | Alta | Actualizar storefront a 14.2.23; estandarizar versiones en ambas apps |
| Zod v3 (storefront) vs v4 (backoffice) — APIs incompatibles | Media | Alta | Migrar storefront a Zod v4; unificar resolvers de react-hook-form |
| `@hookform/resolvers` v3.9 (storefront) vs v5.2 (backoffice) — breaking changes entre versiones | Media | Alta | Estandarizar a la versión más reciente en ambas apps |
| Backoffice sin `output: "standalone"` en next.config.mjs — imagen Docker más pesada | Media | Alta | Agregar `output: "standalone"` al backoffice y ajustar el Dockerfile |
| node_modules dentro de la imagen Docker — cambios de deps requieren `-V` al recrear | Media | Media | Documentar el proceso; usar volúmenes con nombre explícito y rebuild consciente |
| Sin cobertura de tests en el frontend — ningún directorio `tests/` o `__tests__/` detectado | Alta | Alta | Agregar tests con Jest + Testing Library para componentes críticos (checkout, auth, cart) |
| `google_maps_api_key` retornada por endpoint público sin autenticación (`/api/v1/public/platform-settings`) | Alta | Media | Restringir con rate limiting en nginx; considerar proxy del lado del servidor para no exponer la key al cliente |
| Estado de autenticación en Zustand (memoria) — se pierde al recargar si no hay persistencia correcta | Media | Media | Verificar que `useAuth` persiste correctamente en localStorage y maneja expiración de token |
| WebSocket sin reconexión automática robusta en `useOrderTracking` — pérdida de conexión en mobile | Media | Media | Implementar backoff exponencial en la lógica de reconexión del hook |
| Monorepo sin root `package.json` — no hay scripts unificados para lint/test de todo el proyecto | Baja | Alta | Agregar un `package.json` raíz con scripts de workspace o usar Turborepo/nx |
| `X-Tenant-Slug` inyectado por nginx — si nginx está mal configurado el storefront no funciona | Alta | Baja | Tests de integración que validen el routing nginx; health checks por tenant |
| Imágenes de producto con fallback a `/placeholder-product.svg` — UX degradada si CDN falla | Baja | Media | Monitorear errores de carga de imágenes; considerar lazy loading con skeleton |
| `suppressHydrationWarning` en `<html>` — puede enmascarar hydration mismatches reales | Baja | Media | Limitar el uso a lo estrictamente necesario para el anti-FOUC del dark mode |
| Sin CONTRIBUTING.md ni guía de PR en el repo frontend | Baja | Alta | Documentar el flujo `feature/* → stage → main` en CONTRIBUTING.md |
| Dependencia de `sessionStorage` para selección de sucursal — se pierde al cerrar el tab | Baja | Media | Evaluar si `localStorage` o query param es más adecuado según el UX deseado |
