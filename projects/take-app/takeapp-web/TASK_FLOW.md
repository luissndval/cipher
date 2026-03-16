# TASK_FLOW — takeapp-web

## Flujo de trabajo
1. Crear branch desde `stage`: `git checkout stage && git pull origin stage && git checkout -b feature/nombre-ui`
2. Desarrollar la feature (hot reload vía Docker bind mounts)
3. Commitear con conventional commits en inglés: `feat:`, `fix:`, `chore:`, `refactor:`
4. Push y abrir PR hacia `stage`
5. CI corre (type-check + lint) en GitHub Actions
6. Merge a `stage` → deploy automático al entorno de stage (andesit.io)
7. Validar en stage; si OK → abrir PR de `stage` → `main`
8. Merge a `main` → deploy automático a producción (VM GCP)

## Convención de ramas
- `feature/nombre-ui` — nuevas features del frontend
- `fix/descripcion` — correcciones de bugs
- `stage` — integración y testing (recibe PRs de feature)
- `main` — producción estable

> Los PRs van siempre `feature/*` → `stage`, nunca directo a `main`.

## Pull Requests
- Todo PR hacia `stage` debe pasar el workflow de CI (type-check + lint)
- PR de `stage` → `main` requiere revisión manual — cuidado con no incluir archivos exclusivos de stage (`sync-stage.yml` mantiene `stage` al día con `main` automáticamente via merge inverso)
- Antes de mergear a `main`, validar visualmente en `https://{slug}-stage.andesit.io/`

## CI/CD detectado
- `.github/workflows/trigger-deploy.yml` — dispara deploy en la VM GCP vía self-hosted runner
- `.github/workflows/sync-stage.yml` — en cada push a `main`, hace merge automático de `main` → `stage` para mantener stage actualizado

## Comandos útiles de desarrollo
```bash
# Levantar stack completo
cd take-app/infra && docker compose up -d

# Rebuild frontend con limpieza de node_modules
docker compose up --build --force-recreate -V storefront backoffice -d

# Ver logs
docker compose logs -f storefront
docker compose logs -f backoffice
```
