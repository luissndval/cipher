#!/usr/bin/env bash
# populate-context.sh — Analiza un repo git y genera contexto automáticamente con IA
#
# Uso:
#   bash scripts/populate-context.sh <git-url-o-ruta-local> [client-name] [project-name]
#
# Ejemplos:
#   # URL remota
#   bash scripts/populate-context.sh git@github.com:org/backend.git acme-corp backend
#   bash scripts/populate-context.sh https://github.com/org/app.git
#
#   # Ruta local (repo ya descargado)
#   bash scripts/populate-context.sh ~/Projects/take-app/TAKE-APP-BE take-app TAKE-APP-BE
#   bash scripts/populate-context.sh .   # desde dentro del repo
#
# Si no se especifican client-name y project-name, se derivan del nombre del repo.
# Requiere: git, claude CLI

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROMPT_TEMPLATE="$BRAIN_DIR/schemas/POPULATE_PROMPT.md"

BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; DIM='\033[2m'; NC='\033[0m'

# Convierte /c/Users/... → C:/Users/... para que Python pueda abrir el archivo en Windows/Git Bash
to_win_path() {
  local p="$1"
  if [[ "$p" =~ ^/([a-zA-Z])/(.*) ]]; then
    echo "${BASH_REMATCH[1]^^}:/${BASH_REMATCH[2]}"
  else
    echo "$p"
  fi
}

err()  { echo -e "${RED}[populate] $*${NC}" >&2; exit 1; }
warn() { echo -e "${YELLOW}[populate] $*${NC}" >&2; }
ok()   { echo -e "${GREEN}[populate] $*${NC}" >&2; }
info() { echo -e "${DIM}[populate] $*${NC}" >&2; }
step() { echo -e "${BOLD}[populate] $*${NC}" >&2; }

# ── Argumentos ────────────────────────────────────────────────────────────────
SOURCE="${1:-}"
CLIENT_NAME="${2:-}"
PROJECT_NAME="${3:-}"

[[ -z "$SOURCE" ]] && err "Uso: bash scripts/populate-context.sh <git-url-o-ruta-local> [client-name] [project-name]"

# Verificar dependencias
command -v git    &>/dev/null || err "git no está instalado."
command -v claude &>/dev/null || err "Claude CLI no está instalado. Instálalo con: npm install -g @anthropic-ai/claude-code"

# ── 1. Resolver fuente: URL remota o ruta local ───────────────────────────────
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# Detectar si es ruta local o URL
if [[ -d "$SOURCE" ]] || [[ "$SOURCE" == "." ]]; then
  step "1/5 Usando repo local..."
  REPO_DIR="$(cd "$SOURCE" && pwd)"
  # Verificar que es un repo git
  git -C "$REPO_DIR" rev-parse --show-toplevel &>/dev/null \
    || err "La ruta '$SOURCE' no es un repositorio git."
  REPO_BASENAME="$(basename "$(git -C "$REPO_DIR" rev-parse --show-toplevel)")"
  ok "Repo local: $REPO_DIR"
else
  step "1/5 Clonando repo remoto..."
  REPO_BASENAME=$(basename "$SOURCE" .git)
  git clone --depth=1 "$SOURCE" "$TMP_DIR/repo" 2>/dev/null \
    || err "No se pudo clonar el repo: $SOURCE"
  REPO_DIR="$TMP_DIR/repo"
  ok "Repo clonado: $REPO_DIR"
fi

# Derivar nombres si no se especificaron
[[ -z "$PROJECT_NAME" ]] && PROJECT_NAME="$REPO_BASENAME"

# ── 2. Extraer información del repo ──────────────────────────────────────────
step "2/5 Extrayendo información del repo..."

REPO_INFO=""

# Nombre y URL
REPO_INFO+="## Repo\n"
REPO_INFO+="- Nombre: $REPO_BASENAME\n"
REPO_INFO+="- Fuente: $SOURCE\n\n"

# Árbol de archivos (depth 3, excluir node_modules, .git, etc.)
REPO_INFO+="## Árbol de archivos\n\`\`\`\n"
if command -v tree &>/dev/null; then
  REPO_INFO+="$(tree "$REPO_DIR" -L 3 -I 'node_modules|.git|__pycache__|.next|dist|build|vendor|.venv|venv' 2>/dev/null | head -80)\n"
else
  REPO_INFO+="$(find "$REPO_DIR" -maxdepth 3 -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/__pycache__/*' -not -path '*/dist/*' -not -path '*/build/*' -not -path '*/vendor/*' -not -path '*/.venv/*' | sed "s|$REPO_DIR/||" | sort | head -80)\n"
fi
REPO_INFO+="\`\`\`\n\n"

# README
for readme in README.md README.rst README.txt readme.md; do
  if [[ -f "$REPO_DIR/$readme" ]]; then
    REPO_INFO+="## $readme\n\`\`\`\n$(head -150 "$REPO_DIR/$readme")\n\`\`\`\n\n"
    break
  fi
done

# Archivos de dependencias
for dep_file in package.json requirements.txt Pipfile pyproject.toml Cargo.toml go.mod composer.json Gemfile build.gradle pom.xml; do
  fp="$REPO_DIR/$dep_file"
  [[ -f "$fp" ]] && REPO_INFO+="## $dep_file\n\`\`\`\n$(cat "$fp" | head -100)\n\`\`\`\n\n"
done

# Docker / infraestructura
for infra_file in docker-compose.yml docker-compose.yaml Dockerfile .env.example; do
  fp="$REPO_DIR/$infra_file"
  [[ -f "$fp" ]] && REPO_INFO+="## $infra_file\n\`\`\`\n$(cat "$fp" | head -60)\n\`\`\`\n\n"
done

# CI/CD
for ci_dir in .github/workflows .circleci; do
  if [[ -d "$REPO_DIR/$ci_dir" ]]; then
    REPO_INFO+="## CI/CD ($ci_dir)\n"
    REPO_INFO+="$(ls "$REPO_DIR/$ci_dir" 2>/dev/null | head -10)\n\n"
    # Leer primer workflow
    first_workflow=$(ls "$REPO_DIR/$ci_dir"/*.yml 2>/dev/null | head -1)
    [[ -n "$first_workflow" ]] && REPO_INFO+="\`\`\`\n$(cat "$first_workflow" | head -50)\n\`\`\`\n\n"
  fi
done

# Archivos principales de código fuente (muestra)
REPO_INFO+="## Archivos de código principales (muestra)\n"
for ext in ts js py go rs java; do
  main_files=$(find "$REPO_DIR/src" "$REPO_DIR/app" "$REPO_DIR/lib" "$REPO_DIR/cmd" 2>/dev/null \
    -maxdepth 4 -name "*.${ext}" -not -path '*/node_modules/*' | head -3)
  for f in $main_files; do
    rel="${f#$REPO_DIR/}"
    REPO_INFO+="\n### $rel\n\`\`\`\n$(head -60 "$f")\n\`\`\`\n"
  done
done

ok "Información extraída"

# ── 3. Preparar carpetas de destino ───────────────────────────────────────────
step "3/5 Preparando carpetas..."

if [[ -n "$CLIENT_NAME" ]]; then
  PROJECT_PATH="$CLIENT_NAME/$PROJECT_NAME"
  PROJECT_DIR="$BRAIN_DIR/projects/$CLIENT_NAME/$PROJECT_NAME"
  CLIENT_DIR="$BRAIN_DIR/clients/$CLIENT_NAME"

  # Crear cliente si no existe
  if [[ ! -d "$CLIENT_DIR" ]]; then
    cp -r "$BRAIN_DIR/clients/_template" "$CLIENT_DIR"
    warn "Cliente '$CLIENT_NAME' creado desde template — recuerda editar clients/$CLIENT_NAME/CLIENT_PROFILE.md"
  fi
else
  PROJECT_PATH="$PROJECT_NAME"
  PROJECT_DIR="$BRAIN_DIR/projects/$PROJECT_NAME"
fi

mkdir -p "$PROJECT_DIR"
# Copiar CURRENT_TASK.md desde template al REPO (no a brain-contexts) si no existe
REPO_TASK="$REPO_DIR/CURRENT_TASK.md"
if [[ ! -f "$REPO_TASK" ]]; then
  cp "$BRAIN_DIR/projects/_template/CURRENT_TASK.md" "$REPO_TASK"
  info "CURRENT_TASK.md copiado en la raíz del repo"
fi
# Agregar CURRENT_TASK.md al .gitignore del repo si no está ya
REPO_GITIGNORE="$REPO_DIR/.gitignore"
if [[ -f "$REPO_GITIGNORE" ]]; then
  grep -qxF "CURRENT_TASK.md" "$REPO_GITIGNORE" || echo "CURRENT_TASK.md" >> "$REPO_GITIGNORE"
else
  echo "CURRENT_TASK.md" > "$REPO_GITIGNORE"
fi
# Crear CHANGELOG.md y carpeta history/ si no existen
[[ ! -f "$PROJECT_DIR/CHANGELOG.md" ]] && \
  cp "$BRAIN_DIR/projects/_template/CHANGELOG.md" "$PROJECT_DIR/CHANGELOG.md"
mkdir -p "$PROJECT_DIR/history"
ok "Directorio: $PROJECT_DIR"

# ── 4. Generar archivos con Claude ────────────────────────────────────────────
step "4/5 Generando contexto con Claude..."

INSTRUCTIONS=$(cat "$PROMPT_TEMPLATE")

CONTEXT_FILES=(
  "BUSINESS_RULES.md"
  "DEPENDENCIES.md"
  "TECHNICAL_STATE.md"
  "RISK_MATRIX.md"
  "IMPACT_RULES.md"
  "TASK_FLOW.md"
  "TEST_STRATEGY.md"
)

for context_file in "${CONTEXT_FILES[@]}"; do
  info "Generando $context_file..."

  SECTION=$(echo "$context_file" | sed 's/\.md//')

  PROMPT="$(printf '%s\n\n---\n\n# REPO_INFO\n\n%s\n\n---\n\nGenera ÚNICAMENTE el contenido del archivo %s para este proyecto.\nSigue exactamente el formato especificado en las instrucciones para %s.\nIMPORTANTE: responde DIRECTAMENTE con el contenido markdown. NO uses code fences de markdown (no escribas \`\`\`markdown ni \`\`\` al inicio o final). El archivo empieza directamente con el encabezado #.' \
    "$INSTRUCTIONS" "$REPO_INFO" "$context_file" "$SECTION")"

  OUTPUT=$(echo "$PROMPT" | claude -p --output-format text 2>/dev/null)

  if [[ -n "$OUTPUT" ]]; then
    echo "$OUTPUT" > "$PROJECT_DIR/$context_file"
    ok "$context_file generado"
  else
    warn "$context_file no pudo generarse — se dejó el template"
    # Copiar template si no existe
    template_file="$BRAIN_DIR/projects/_template/$context_file"
    [[ -f "$template_file" && ! -f "$PROJECT_DIR/$context_file" ]] && cp "$template_file" "$PROJECT_DIR/$context_file"
  fi
done

# ── 5. Registrar en context-map.json ─────────────────────────────────────────
step "5/5 Registrando en context-map.json..."

MAP="$BRAIN_DIR/context-map.json"
MAP_NATIVE=$(to_win_path "$MAP")

if command -v python3 &>/dev/null; then
  python3 - "$MAP_NATIVE" "$REPO_BASENAME" "$PROJECT_PATH" <<'PYEOF'
import json, sys
map_path, repo, project_path = sys.argv[1], sys.argv[2], sys.argv[3]
with open(map_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
data['mappings'][repo] = project_path
with open(map_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write('\n')
print('context-map.json actualizado')
PYEOF
  ok "context-map.json actualizado"
elif command -v jq &>/dev/null; then
  tmp=$(mktemp)
  jq --arg repo "$REPO_BASENAME" --arg path "$PROJECT_PATH" \
    '.mappings[$repo] = $path' "$MAP" > "$tmp" && mv "$tmp" "$MAP"
  ok "context-map.json actualizado"
else
  warn "No se pudo actualizar context-map.json automáticamente (instala python3 o jq)."
  warn "Agrega manualmente: \"$REPO_BASENAME\": \"$PROJECT_PATH\""
fi

# ── Resumen ───────────────────────────────────────────────────────────────────
echo ""
ok "Contexto generado para: $PROJECT_PATH"
echo ""
echo -e "${BOLD}Archivos creados en:${NC} projects/$PROJECT_PATH/"
echo ""
echo -e "${BOLD}Próximos pasos:${NC}"
echo "  1. Revisa y ajusta los .md generados en projects/$PROJECT_PATH/"
[[ -n "$CLIENT_NAME" ]] && echo "  2. Completa clients/$CLIENT_NAME/CLIENT_PROFILE.md"
echo "  3. Commitea los cambios en brain-contexts"
echo "  4. Ve al repo y ejecuta: brain claude"
