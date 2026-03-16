# TASK_FLOW — takeapp-api

## Flujo de trabajo
1. Crear rama `feature/*` desde `stage`
2. Desarrollar y commitear con conventional commits en inglés
3. Hacer push y abrir PR hacia `stage`
4. CI corre automáticamente (tests + lint)
5. Merge a `stage` → deploy automático al entorno stage (andesit.io)
6. Validar en stage
7. Abrir PR desde `stage` → `main` (revisar que no entren archivos stage-only)
8. Merge a `main` → deploy automático a producción (VM GCP)

## Convención de ramas
- `feature/<nombre-corto>` — nueva funcionalidad o fix, sale de `stage`
- `stage` — integración y testing pre-producción
- `main` — código estable en producción; releases marcados con tags (`v1.0.0`, `v1.1.0`)

## Comandos por repo (backend)
```bash
cd take-app/takeapp-api
git pull origin stage && git checkout -b feature/nombre
git add <archivos>
git commit -m "feat: descripcion"
git push -u origin feature/nombre
```

## Pull Requests
- Los PRs de features van **siempre** a `stage`, nunca directo a `main`
- El CI (`.github/workflows`) corre pytest + type-check antes del merge
- Para promover a producción: PR desde `stage` → `main`, revisando manualmente que no se incluyan archivos exclusivos de stage (`docker-compose.stage.yml`, `nginx-stage-internal.conf`, `host-nginx.conf`)
- Tags semánticos en `main` para marcar cada release

## CI/CD
- `.github/workflows/sync-stage.yml` — al hacer push a `main`, mergea automáticamente `main` → `stage` para mantenerla sincronizada
- `.github/workflows/trigger-deploy.yml` — dispara el deploy en el self-hosted runner de la VM GCP
- El runner ejecuta: `git pull` en los 3 repos + `docker compose up --build -d` + (opcional) `alembic upgrade head`

## Migraciones
```bash
# Generar migración nueva
docker exec takeapp-backend alembic revision --autogenerate -m "descripcion"

# Aplicar
docker exec takeapp-backend alembic upgrade head
```
Las migraciones deben incluirse en el mismo PR que los cambios de modelo. Convención de nombre: `NNN_descripcion_corta.py`.

## Seeds
```bash
# Planes Starter/Pro/Scale (upsert — seguro de re-correr)
docker exec takeapp-backend python -m app.seeds.plans

# Datos de desarrollo
docker exec takeapp-backend python /app/scripts/seed_laburgueria.py
```
