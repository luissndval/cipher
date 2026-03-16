# TEST_STRATEGY — takeapp-web

## Frameworks
- Ninguno detectado activamente configurado en el monorepo frontend

## Comandos
```bash
# No hay scripts de test definidos en package.json de ninguna de las dos apps
# Si se configurara Jest o Vitest:
# cd apps/storefront && npm test
# cd apps/backoffice && npm test
```

## Qué se prueba
- **Storefront**: Sin cobertura de tests detectada
- **Backoffice**: Sin cobertura de tests detectada
- **CI**: El workflow de CI del repo principal (TAKE-APP) ejecuta type-check y lint del frontend, pero no tests funcionales

## Qué NO se prueba (gaps identificados)
- Lógica de negocio en hooks (`useAuth`, `useFeatures`, `useOrderTracking`, `useBusinessLabels`)
- Store de Zustand (`cart.ts`) — persistencia, agregado/eliminación de ítems, cálculo de totales
- Componentes críticos: `ProductOptionsModal`, `OptionGroupsEditor`, `BranchSelector`
- Flujo de checkout end-to-end (selección de delivery, pago MercadoPago)
- Middleware multi-tenant (`middleware.ts`) — rewrite por `X-Tenant-Slug`
- Resolución de feature flags en `useFeatures`
- Dark mode anti-FOUC (script síncrono en `<head>`)
- Validaciones Zod de formularios (react-hook-form + zodResolver)
- Integración con WebSocket (`useOrderTracking`, vista cocina)

<!-- TODO: completar — evaluar adoptar Vitest + React Testing Library para cobertura de hooks y componentes críticos; Playwright para e2e de flujos de checkout y tracking -->
