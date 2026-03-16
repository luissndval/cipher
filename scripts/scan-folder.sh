#!/usr/bin/env bash
# scan-folder.sh — Escanea una carpeta buscando repos git y genera contexto por cada uno
#
# Uso:
#   bash scripts/scan-folder.sh <carpeta> [client-name]
#
# Ejemplos:
#   bash scripts/scan-folder.sh ~/Projects/take-app take-app
#   bash scripts/scan-folder.sh ~/Projects/acme-corp acme-corp
#
# Para cada subcarpeta que sea un repo git, pregunta:
#   [s] Sí — generar contexto
#   [n] No — saltar
#   [t] Terminar — detener el proceso

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; DIM='\033[2m'; CYAN='\033[0;36m'; NC='\033[0m'

err()  { echo -e "${RED}[scan] $*${NC}" >&2; exit 1; }
warn() { echo -e "${YELLOW}[scan] $*${NC}" >&2; }
ok()   { echo -e "${GREEN}[scan] $*${NC}" >&2; }
info() { echo -e "${DIM}[scan] $*${NC}" >&2; }
step() { echo -e "${BOLD}[scan] $*${NC}" >&2; }

# ── Argumentos ────────────────────────────────────────────────────────────────
SCAN_DIR="${1:-}"
CLIENT_NAME="${2:-}"

[[ -z "$SCAN_DIR" ]] && err "Uso: bash scripts/scan-folder.sh <carpeta> [client-name]"
[[ -d "$SCAN_DIR" ]] || err "La carpeta '$SCAN_DIR' no existe."

SCAN_DIR="$(cd "$SCAN_DIR" && pwd)"

# Si no se especificó cliente, preguntar
if [[ -z "$CLIENT_NAME" ]]; then
  echo ""
  echo -e "${BOLD}Nombre del cliente para estos repos (Enter para omitir):${NC}"
  read -r CLIENT_NAME
fi

echo ""
step "Escaneando: $SCAN_DIR"
[[ -n "$CLIENT_NAME" ]] && info "Cliente: $CLIENT_NAME"
echo ""

# ── Buscar subcarpetas que sean repos git ─────────────────────────────────────
REPOS=()
for subdir in "$SCAN_DIR"/*/; do
  [[ -d "$subdir/.git" ]] && REPOS+=("$subdir")
done

if [[ ${#REPOS[@]} -eq 0 ]]; then
  err "No se encontraron repositorios git en '$SCAN_DIR'."
fi

ok "Repos encontrados: ${#REPOS[@]}"
echo ""

# ── Listar repos detectados ───────────────────────────────────────────────────
echo -e "${BOLD}Repos detectados:${NC}"
for repo in "${REPOS[@]}"; do
  echo -e "  ${CYAN}$(basename "$repo")${NC}"
done
echo ""

# ── Procesar cada repo ────────────────────────────────────────────────────────
PROCESSED=0
SKIPPED=0

for repo_path in "${REPOS[@]}"; do
  REPO_NAME="$(basename "$repo_path")"

  echo -e "${BOLD}──────────────────────────────────────────${NC}"
  echo -e "  Repo: ${CYAN}$REPO_NAME${NC}"
  echo -e "  Ruta: ${DIM}$repo_path${NC}"
  echo ""

  # Mostrar info básica del repo
  lang=""
  [[ -f "$repo_path/package.json" ]]      && lang="Node.js"
  [[ -f "$repo_path/requirements.txt" ]]  && lang="Python"
  [[ -f "$repo_path/go.mod" ]]            && lang="Go"
  [[ -f "$repo_path/Cargo.toml" ]]        && lang="Rust"
  [[ -f "$repo_path/composer.json" ]]     && lang="PHP"
  [[ -f "$repo_path/pom.xml" ]]           && lang="Java"
  [[ -n "$lang" ]] && info "Lenguaje detectado: $lang"

  # Ya registrado?
  ALREADY_MAPPED=false
  if command -v python3 &>/dev/null; then
    MAPPED=$(python3 -c "
import json, sys
with open('$BRAIN_DIR/context-map.json') as f:
    d = json.load(f)
print(d.get('mappings', {}).get('$REPO_NAME', ''))
" 2>/dev/null)
    [[ -n "$MAPPED" ]] && ALREADY_MAPPED=true
  fi

  if $ALREADY_MAPPED; then
    warn "Ya registrado en context-map.json → '$MAPPED'"
    echo -e "  ${DIM}¿Regenerar contexto? [s/n/t]${NC} " && read -r choice
  else
    echo -e "  ${BOLD}¿Generar contexto para este repo? [s/n/t]${NC} " && read -r choice
  fi

  echo ""

  case "${choice,,}" in
    s|si|sí|y|yes)
      if [[ -n "$CLIENT_NAME" ]]; then
        bash "$SCRIPT_DIR/populate-context.sh" "$repo_path" "$CLIENT_NAME" "$REPO_NAME"
      else
        bash "$SCRIPT_DIR/populate-context.sh" "$repo_path" "" "$REPO_NAME"
      fi
      ((PROCESSED++))
      ;;
    t|terminar|q|quit|exit)
      echo ""
      warn "Proceso terminado por el usuario."
      break
      ;;
    *)
      info "Saltando $REPO_NAME..."
      ((SKIPPED++))
      ;;
  esac

  echo ""
done

# ── Resumen ───────────────────────────────────────────────────────────────────
echo -e "${BOLD}──────────────────────────────────────────${NC}"
echo ""
ok "Proceso completado."
echo -e "  Procesados: ${GREEN}$PROCESSED${NC}"
echo -e "  Saltados:   ${YELLOW}$SKIPPED${NC}"
echo ""

if [[ $PROCESSED -gt 0 ]]; then
  echo -e "${BOLD}Próximos pasos:${NC}"
  echo "  1. Revisa los .md generados en projects/"
  [[ -n "$CLIENT_NAME" ]] && echo "  2. Completa clients/$CLIENT_NAME/CLIENT_PROFILE.md"
  echo "  3. Commitea: git add -A && git commit -m 'feat: add context for $CLIENT_NAME'"
  echo "  4. Ve a cada repo y ejecuta: brain claude"
fi
