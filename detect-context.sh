#!/usr/bin/env bash
# detect-context.sh — Genera contexto del proyecto y lanza el agente IA
#
# Uso:
#   bash detect-context.sh              → genera contexto, imprime ruta
#   bash detect-context.sh claude       → genera contexto + lanza Claude Code
#   bash detect-context.sh gemini       → genera contexto + lanza Gemini CLI
#   bash detect-context.sh aider        → genera contexto + lanza Aider
#
# Variables de entorno:
#   BRAIN_CONTEXTS   → ruta a brain-contexts (default: directorio de este script)

set -uo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_CONTEXTS="${BRAIN_CONTEXTS:-$SCRIPT_DIR}"
AGENT="${1:-}"

# ── Colores ───────────────────────────────────────────────────────────────────
BOLD='\033[1m'; DIM='\033[2m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

err()  { echo -e "${RED}[brain] $*${NC}" >&2; exit 1; }
warn() { echo -e "${YELLOW}[brain] $*${NC}" >&2; }
ok()   { echo -e "${GREEN}[brain] $*${NC}" >&2; }
info() { echo -e "${DIM}[brain] $*${NC}" >&2; }

# ── 1. Detectar repo actual ───────────────────────────────────────────────────
git rev-parse --show-toplevel &>/dev/null \
  || err "No estás en un repositorio git. Navega a tu proyecto primero."

REPO_ROOT="$(git rev-parse --show-toplevel)"
REPO_NAME="$(basename "$REPO_ROOT")"
info "Repo: $REPO_NAME"

# ── 2. Resolver proyecto desde context-map.json ───────────────────────────────
MAP="$BRAIN_CONTEXTS/context-map.json"
[[ -f "$MAP" ]] || err "context-map.json no encontrado en $BRAIN_CONTEXTS"

if command -v python3 &>/dev/null; then
  PROJECT=$(python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
print(d.get('mappings', {}).get('$REPO_NAME', d.get('default', '_template')))
" < "$MAP")
elif command -v jq &>/dev/null; then
  PROJECT=$(jq -r --arg r "$REPO_NAME" '.mappings[$r] // .default' "$MAP")
else
  err "Necesitas python3 o jq instalado."
fi

# ── 3. Resolver capa cliente (si el path es cliente/proyecto) ─────────────────
# PROJECT puede ser:
#   "acme-corp/backend-api"  → CLIENT=acme-corp, PROJECT_SLUG=backend-api
#   "_template"              → sin cliente
#   "standalone-project"     → sin cliente (estructura legacy)

CLIENT=""
PROJECT_SLUG="$PROJECT"

if [[ "$PROJECT" == */* ]]; then
  CLIENT="${PROJECT%%/*}"
  PROJECT_SLUG="${PROJECT#*/}"
fi

PROJECT_DIR="$BRAIN_CONTEXTS/projects/$PROJECT"

# ── Flujo de primer uso: repo no mapeado ─────────────────────────────────────
if [[ "$PROJECT" == "_template" || ! -d "$PROJECT_DIR" ]]; then
  echo "" >&2
  warn "El repo '$REPO_NAME' no está registrado en context-map.json."
  echo "" >&2

  # Detectar si el directorio padre tiene más repos git (carpeta de cliente)
  PARENT_DIR="$(dirname "$REPO_ROOT")"
  SIBLING_REPOS=()
  for sibling in "$PARENT_DIR"/*/; do
    [[ -d "$sibling/.git" && "$sibling" != "$REPO_ROOT/" ]] && SIBLING_REPOS+=("$sibling")
  done

  if [[ ${#SIBLING_REPOS[@]} -gt 0 ]]; then
    PARENT_NAME="$(basename "$PARENT_DIR")"
    echo -e "${BOLD}  Se detectó que '$(basename "$PARENT_DIR")/' contiene múltiples repos:${NC}" >&2
    echo -e "  ${DIM}$(basename "$REPO_ROOT")${NC} ← actual" >&2
    for s in "${SIBLING_REPOS[@]}"; do
      echo -e "  ${DIM}$(basename "$s")${NC}" >&2
    done
    echo "" >&2
    echo -e "${BOLD}  ¿Escanear toda la carpeta '$PARENT_NAME' de una vez? [s/n]${NC} " >&2
    read -r SCAN_CHOICE

    if [[ "${SCAN_CHOICE,,}" == "s" || "${SCAN_CHOICE,,}" == "si" || "${SCAN_CHOICE,,}" == "sí" ]]; then
      echo "" >&2
      echo -e "  Nombre del cliente (Enter para usar '$PARENT_NAME'):" >&2
      read -r CLIENT_INPUT
      [[ -z "$CLIENT_INPUT" ]] && CLIENT_INPUT="$PARENT_NAME"

      bash "$BRAIN_CONTEXTS/scripts/scan-folder.sh" "$PARENT_DIR" "$CLIENT_INPUT"

      # Re-resolver luego del scan
      if command -v python3 &>/dev/null; then
        PROJECT=$(python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
print(d.get('mappings', {}).get('$REPO_NAME', d.get('default', '_template')))
" < "$MAP")
      elif command -v jq &>/dev/null; then
        PROJECT=$(jq -r --arg r "$REPO_NAME" '.mappings[$r] // .default' "$MAP")
      fi
      PROJECT_DIR="$BRAIN_CONTEXTS/projects/$PROJECT"

    else
      # Solo este repo
      echo "" >&2
      echo -e "${BOLD}  ¿Generar contexto solo para '$REPO_NAME'? [s/n]${NC} " >&2
      read -r SINGLE_CHOICE

      if [[ "${SINGLE_CHOICE,,}" == "s" || "${SINGLE_CHOICE,,}" == "si" || "${SINGLE_CHOICE,,}" == "sí" ]]; then
        echo "" >&2
        echo -e "  Nombre del cliente (opcional, Enter para omitir):" >&2
        read -r CLIENT_INPUT

        if [[ -n "$CLIENT_INPUT" ]]; then
          bash "$BRAIN_CONTEXTS/scripts/populate-context.sh" "$REPO_ROOT" "$CLIENT_INPUT" "$REPO_NAME"
        else
          bash "$BRAIN_CONTEXTS/scripts/populate-context.sh" "$REPO_ROOT" "" "$REPO_NAME"
        fi

        if command -v python3 &>/dev/null; then
          PROJECT=$(python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
print(d.get('mappings', {}).get('$REPO_NAME', d.get('default', '_template')))
" < "$MAP")
        elif command -v jq &>/dev/null; then
          PROJECT=$(jq -r --arg r "$REPO_NAME" '.mappings[$r] // .default' "$MAP")
        fi
        PROJECT_DIR="$BRAIN_CONTEXTS/projects/$PROJECT"
      else
        warn "Usando template vacío. Registra el repo en context-map.json cuando estés listo."
        PROJECT_DIR="$BRAIN_CONTEXTS/projects/_template"
      fi
    fi

  else
    # Solo un repo, sin hermanos — flujo directo
    echo -e "${BOLD}  ¿Generar contexto para '$REPO_NAME'? [s/n]${NC} " >&2
    read -r SINGLE_CHOICE

    if [[ "${SINGLE_CHOICE,,}" == "s" || "${SINGLE_CHOICE,,}" == "si" || "${SINGLE_CHOICE,,}" == "sí" ]]; then
      echo "" >&2
      echo -e "  Nombre del cliente (opcional, Enter para omitir):" >&2
      read -r CLIENT_INPUT

      if [[ -n "$CLIENT_INPUT" ]]; then
        bash "$BRAIN_CONTEXTS/scripts/populate-context.sh" "$REPO_ROOT" "$CLIENT_INPUT" "$REPO_NAME"
      else
        bash "$BRAIN_CONTEXTS/scripts/populate-context.sh" "$REPO_ROOT" "" "$REPO_NAME"
      fi

      if command -v python3 &>/dev/null; then
        PROJECT=$(python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
print(d.get('mappings', {}).get('$REPO_NAME', d.get('default', '_template')))
" < "$MAP")
      elif command -v jq &>/dev/null; then
        PROJECT=$(jq -r --arg r "$REPO_NAME" '.mappings[$r] // .default' "$MAP")
      fi
      PROJECT_DIR="$BRAIN_CONTEXTS/projects/$PROJECT"
    else
      warn "Usando template vacío. Registra el repo en context-map.json cuando estés listo."
      PROJECT_DIR="$BRAIN_CONTEXTS/projects/_template"
    fi
  fi
fi

[[ -d "$PROJECT_DIR" ]] || err "Carpeta de proyecto no encontrada: $PROJECT_DIR"

CLIENT_DIR=""
if [[ -n "$CLIENT" ]]; then
  CLIENT_DIR="$BRAIN_CONTEXTS/clients/$CLIENT"
  info "Cliente: $CLIENT"
fi
info "Proyecto: $PROJECT_SLUG"

# ── 4. Construir ACTIVE_CONTEXT.md ───────────────────────────────────────────
OUTPUT_DIR="$BRAIN_CONTEXTS/output"
mkdir -p "$OUTPUT_DIR"
CONTEXT_FILE="$OUTPUT_DIR/ACTIVE_CONTEXT.md"

{
  echo "<!-- ACTIVE_CONTEXT — generado automáticamente, no editar -->"
  echo "<!-- Repo: $REPO_NAME | Cliente: ${CLIENT:-none} | Proyecto: $PROJECT_SLUG | $(date '+%Y-%m-%d %H:%M') -->"
  echo ""

  # Capa global
  echo "---"
  echo "## CAPA GLOBAL"
  echo ""
  for f in GLOBAL_RULES.md AGENT.md FALLBACK_CONTEXT.md; do
    fp="$BRAIN_CONTEXTS/global/$f"
    [[ -f "$fp" ]] && cat "$fp" && echo ""
  done

  # Capa cliente (solo si existe)
  if [[ -n "$CLIENT_DIR" && -d "$CLIENT_DIR" ]]; then
    echo "---"
    echo "## CAPA CLIENTE: $CLIENT"
    echo ""
    for f in CLIENT_PROFILE.md BILLING_RULES.md TECH_PREFERENCES.md COMMUNICATION.md; do
      fp="$CLIENT_DIR/$f"
      [[ -f "$fp" ]] && cat "$fp" && echo ""
    done
  fi

  # Capa proyecto
  echo "---"
  echo "## CAPA PROYECTO: $PROJECT_SLUG"
  echo ""
  for f in BUSINESS_RULES.md DEPENDENCIES.md RISK_MATRIX.md; do
    fp="$PROJECT_DIR/$f"
    [[ -f "$fp" ]] && cat "$fp" && echo ""
  done

  # Capa estado técnico
  echo "---"
  echo "## ESTADO TÉCNICO ACTUAL"
  echo ""
  fp="$PROJECT_DIR/TECHNICAL_STATE.md"
  [[ -f "$fp" ]] && cat "$fp" && echo ""

  # Capa tarea
  echo "---"
  echo "## CAPA TAREA"
  echo ""
  for f in IMPACT_RULES.md TASK_FLOW.md TEST_STRATEGY.md; do
    fp="$PROJECT_DIR/$f"
    [[ -f "$fp" ]] && cat "$fp" && echo ""
  done

} > "$CONTEXT_FILE"

LINES=$(wc -l < "$CONTEXT_FILE")
ok "Contexto listo → $CONTEXT_FILE ($LINES líneas)"

# ── 5. Lanzar agente si se especificó ────────────────────────────────────────
if [[ -z "$AGENT" ]]; then
  echo "$CONTEXT_FILE"
  exit 0
fi

command -v "$AGENT" &>/dev/null \
  || err "'$AGENT' no está instalado. Instálalo primero."

echo -e "\n${BOLD}Iniciando $AGENT...${NC}\n" >&2
cd "$REPO_ROOT"

case "$AGENT" in
  claude)  exec claude --system-prompt "$CONTEXT_FILE" ;;
  gemini)  exec gemini --system-prompt "$CONTEXT_FILE" ;;
  aider)   exec aider --read "$CONTEXT_FILE" ;;
  *)       err "Agente '$AGENT' no soportado. Usa: claude | gemini | aider" ;;
esac
