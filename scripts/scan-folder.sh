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

# Convierte /c/Users/... → C:/Users/... para que Python pueda abrir el archivo en Windows/Git Bash
to_win_path() {
  local p="$1"
  if [[ "$p" =~ ^/([a-zA-Z])/(.*) ]]; then
    echo "${BASH_REMATCH[1]^^}:/${BASH_REMATCH[2]}"
  else
    echo "$p"
  fi
}

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
    MAP_NATIVE=$(to_win_path "$BRAIN_DIR/context-map.json")
    MAPPED=$(python3 - "$MAP_NATIVE" "$REPO_NAME" <<'PYEOF'
import json, sys
map_path, repo_name = sys.argv[1], sys.argv[2]
with open(map_path, encoding='utf-8') as f:
    d = json.load(f)
print(d.get('mappings', {}).get(repo_name, ''))
PYEOF
    2>/dev/null)
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

  # ── Auto-generar CLIENT_PROFILE.md si hay cliente y sigue siendo el template ──
  if [[ -n "$CLIENT_NAME" ]]; then
    CLIENT_DIR="$BRAIN_DIR/clients/$CLIENT_NAME"
    CLIENT_PROFILE="$CLIENT_DIR/CLIENT_PROFILE.md"

    if [[ -f "$CLIENT_PROFILE" ]] && grep -q "Nombre del Cliente" "$CLIENT_PROFILE" 2>/dev/null; then
      echo ""
      step "Generando CLIENT_PROFILE.md para '$CLIENT_NAME'..."

      PROJECTS_INFO=""
      for repo_path in "${REPOS[@]}"; do
        rname="$(basename "$repo_path")"
        br="$BRAIN_DIR/projects/$CLIENT_NAME/$rname/BUSINESS_RULES.md"
        [[ -f "$br" ]] && PROJECTS_INFO+="### $rname\n$(head -60 "$br")\n\n"
      done

      PROFILE_PROMPT="Eres un asistente que documenta clientes de software.
Basándote en los siguientes repositorios del cliente '$CLIENT_NAME', genera un CLIENT_PROFILE.md conciso.
IMPORTANTE: responde DIRECTAMENTE con el contenido markdown. NO uses code fences de markdown al inicio o final.

Formato:
# CLIENT_PROFILE — $CLIENT_NAME

## Descripción
[quiénes son, a qué se dedican, qué problema resuelven]

## Proyectos
[lista de repos con una línea de descripción cada uno]

## Stack preferido
[tecnologías identificadas en los repos]

## Restricciones conocidas
[limitaciones técnicas o de negocio identificadas — si no hay suficiente info, poner <!-- TODO: completar -->]

## Contactos clave
<!-- TODO: completar -->

## Notas generales
[cualquier patrón o contexto relevante observado]

---
Información de los repos:
$PROJECTS_INFO"

      PROFILE_OUTPUT=$(echo "$PROFILE_PROMPT" | claude -p --output-format text 2>/dev/null)

      if [[ -n "$PROFILE_OUTPUT" ]]; then
        echo "$PROFILE_OUTPUT" > "$CLIENT_PROFILE"
        ok "CLIENT_PROFILE.md generado"
      else
        warn "No se pudo generar CLIENT_PROFILE.md — edítalo manualmente en clients/$CLIENT_NAME/"
      fi
    fi

    # ── Generar INTEGRATION_MAP.md si no existe o sigue siendo el template ──
    INTEGRATION_MAP="$CLIENT_DIR/INTEGRATION_MAP.md"
    if [[ ! -f "$INTEGRATION_MAP" ]] || grep -q "client-name" "$INTEGRATION_MAP" 2>/dev/null; then
      echo ""
      step "Generando INTEGRATION_MAP.md para '$CLIENT_NAME'..."

      REPOS_SUMMARY=""
      for repo_path in "${REPOS[@]}"; do
        rname="$(basename "$repo_path")"
        proj_dir="$BRAIN_DIR/projects/$CLIENT_NAME/$rname"
        for ctx_file in BUSINESS_RULES.md DEPENDENCIES.md; do
          fp="$proj_dir/$ctx_file"
          [[ -f "$fp" ]] && REPOS_SUMMARY+="### $rname / $ctx_file\n$(head -40 "$fp")\n\n"
        done
      done

      MAP_PROMPT="Eres un asistente que documenta contratos de integración entre repositorios.
Analiza la información de los siguientes repos del cliente '$CLIENT_NAME' e infiere los contratos entre ellos.
IMPORTANTE: responde DIRECTAMENTE con el markdown. NO uses code fences al inicio o final.

Formato:
# INTEGRATION_MAP — $CLIENT_NAME

## Contratos HTTP
| Repo proveedor | Endpoint | Repos consumidores | Notas |
|----------------|----------|--------------------|-------|

## Eventos / WebSocket
| Repo emisor | Canal / Evento | Repos receptores |
|-------------|----------------|------------------|

## Schemas / Tipos compartidos
| Repo origen | Schema / Tipo | Repos que lo usan |
|-------------|---------------|-------------------|

## Variables de entorno compartidas
| Variable | Repos que la usan |
|----------|-------------------|

Si no puedes inferir un contrato con certeza, usa <!-- TODO: verificar --> en la celda.

---
Información de repos:
$REPOS_SUMMARY"

      MAP_OUTPUT=$(echo "$MAP_PROMPT" | claude -p --output-format text 2>/dev/null)

      if [[ -n "$MAP_OUTPUT" ]]; then
        echo "$MAP_OUTPUT" > "$INTEGRATION_MAP"
        ok "INTEGRATION_MAP.md generado"
      else
        cp "$BRAIN_DIR/clients/_template/INTEGRATION_MAP.md" "$INTEGRATION_MAP"
        warn "INTEGRATION_MAP.md no pudo generarse — se copió el template en clients/$CLIENT_NAME/"
      fi
    fi
  fi

  echo ""
  echo -e "${BOLD}Próximos pasos:${NC}"
  echo "  1. Revisa los .md generados en projects/"
  [[ -n "$CLIENT_NAME" ]] && echo "  2. Revisa clients/$CLIENT_NAME/CLIENT_PROFILE.md"
  echo "  3. Commitea: git add -A && git commit -m 'feat: add context for $CLIENT_NAME'"
  echo "  4. Ve a cada repo y ejecuta: brain claude"
fi
