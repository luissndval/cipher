#!/usr/bin/env bash
# populate-context.sh — Analiza un repo git y genera contexto automáticamente con IA
#
# Uso:
#   bash scripts/populate-context.sh <git-url> [client-name] [project-name]
#
# Ejemplos:
#   bash scripts/populate-context.sh git@github.com:org/backend.git acme-corp backend
#   bash scripts/populate-context.sh https://github.com/org/app.git
#
# Si no se especifican client-name y project-name, se derivan del nombre del repo.
# Requiere: git, claude CLI

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROMPT_TEMPLATE="$BRAIN_DIR/schemas/POPULATE_PROMPT.md"

BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; DIM='\033[2m'; NC='\033[0m'

err()  { echo -e "${RED}[populate] $*${NC}" >&2; exit 1; }
warn() { echo -e "${YELLOW}[populate] $*${NC}" >&2; }
ok()   { echo -e "${GREEN}[populate] $*${NC}" >&2; }
info() { echo -e "${DIM}[populate] $*${NC}" >&2; }
step() { echo -e "${BOLD}[populate] $*${NC}" >&2; }

# ── Argumentos ────────────────────────────────────────────────────────────────
GIT_URL="${1:-}"
CLIENT_NAME="${2:-}"
PROJECT_NAME="${3:-}"

[[ -z "$GIT_URL" ]] && err "Uso: bash scripts/populate-context.sh <git-url> [client-name] [project-name]"

# Derivar nombre del repo desde la URL
REPO_BASENAME=$(basename "$GIT_URL" .git)

# Si no se especifican, usar el nombre del repo
[[ -z "$PROJECT_NAME" ]] && PROJECT_NAME="$REPO_BASENAME"

# Verificar dependencias
command -v git    &>/dev/null || err "git no está instalado."
command -v claude &>/dev/null || err "Claude CLI no está instalado. Instálalo con: npm install -g @anthropic-ai/claude-code"

# ── 1. Clonar repo en directorio temporal ─────────────────────────────────────
step "1/5 Clonando repo..."
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

git clone --depth=1 "$GIT_URL" "$TMP_DIR/repo" 2>/dev/null \
  || err "No se pudo clonar el repo: $GIT_URL"
ok "Repo clonado en $TMP_DIR/repo"

REPO_DIR="$TMP_DIR/repo"

# ── 2. Extraer información del repo ──────────────────────────────────────────
step "2/5 Extrayendo información del repo..."

REPO_INFO=""

# Nombre y URL
REPO_INFO+="## Repo\n"
REPO_INFO+="- Nombre: $REPO_BASENAME\n"
REPO_INFO+="- URL: $GIT_URL\n\n"

# Árbol de archivos (depth 3, excluir node_modules, .git, etc.)
REPO_INFO+="## Árbol de archivos\n\`\`\`\n"
if command -v tree &>/dev/null; then
  REPO_INFO+="$(tree "$REPO_DIR" -L 3 -I 'node_modules|.git|__pycache__|.next|dist|build|vendor|.venv|venv' 2>/dev/null | head -80)\n"
else
  REPO_INFO+="$(find "$REPO_DIR" -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/__pycache__/*' -not -path '*/dist/*' -not -path '*/build/*' -not -path '*/vendor/*' -not -path '*/.venv/*' -maxdepth 3 | sed "s|$REPO_DIR/||" | sort | head -80)\n"
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
    -name "*.${ext}" -not -path '*/node_modules/*' | head -3)
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

  PROMPT="$(printf '%s\n\n---\n\n# REPO_INFO\n\n%s\n\n---\n\nGenera ÚNICAMENTE el contenido del archivo %s para este proyecto.\nSigue exactamente el formato especificado en las instrucciones para %s.\nResponde solo con el contenido markdown del archivo, sin explicaciones adicionales.' \
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

if command -v python3 &>/dev/null; then
  python3 - <<EOF
import json

with open('$MAP', 'r') as f:
    data = json.load(f)

data['mappings']['$REPO_BASENAME'] = '$PROJECT_PATH'

with open('$MAP', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write('\n')

print('context-map.json actualizado')
EOF
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
