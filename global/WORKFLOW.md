# WORKFLOW — Proceso estándar de la consultora

## GitFlow

```
main          ← producción, siempre estable
develop       ← integración, base para features
feature/xxx   ← desarrollo de features (branch desde develop)
hotfix/xxx    ← fixes urgentes en producción (branch desde main)
release/x.x   ← preparación de release (branch desde develop)
```

### Reglas de branching
- Nunca commitear directo a `main` o `develop`
- Nombre de branch: `feature/TASK-142-descripcion-corta`
- Una branch por ticket
- Eliminar branches merged

## Pull Requests

### Antes de abrir un PR
- [ ] Tests pasando localmente
- [ ] Sin conflictos con `develop`
- [ ] Descripción completa del cambio
- [ ] Ticket referenciado en el título

### Formato de PR
```
[TASK-142] Agregar filtro por fecha en /api/orders

## Qué cambió
- Endpoint /api/orders ahora acepta ?from=&to=
- Nuevo índice en tabla orders por created_at

## Cómo probar
1. GET /api/orders?from=2024-01-01&to=2024-01-31
2. Verificar que retorna solo pedidos en el rango

## Impacto en otros repos
- [ ] Verificar consumidores de /api/orders (ver ALERT.md si existe)
```

### Revisión
- Mínimo 1 aprobación antes de merge
- El autor no puede aprobarse a sí mismo
- CI debe pasar antes del merge

## Proceso de release

1. Crear `release/x.x` desde `develop`
2. Bump de versión en package.json / pyproject.toml
3. Actualizar CHANGELOG
4. PR de `release/x.x` → `main`
5. Tag en `main`: `v1.2.0`
6. Merge `main` → `develop` para sincronizar

## Environments

| Ambiente | Branch | Deploy |
|----------|--------|--------|
| local | cualquiera | manual |
| staging | develop | automático en merge |
| producción | main | manual con aprobación |
