#!/usr/bin/env bash
# install.sh — Instala el comando `brain` en Mac, Linux y Windows (Git Bash)
#
# Uso:
#   bash scripts/install.sh
#
# Qué hace según OS:
#   Mac/Linux  → agrega alias en ~/.bashrc, ~/.zshrc o ~/.bash_profile
#   Windows    → crea brain.bat en ~/scripts y lo agrega al PATH de usuario

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BRAIN_SCRIPT="$BRAIN_DIR/detect-context.sh"

BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

ok()   { echo -e "${GREEN}[install] $*${NC}"; }
warn() { echo -e "${YELLOW}[install] $*${NC}"; }
err()  { echo -e "${RED}[install] $*${NC}" >&2; exit 1; }
info() { echo -e "${BOLD}[install] $*${NC}"; }

# ── Detectar OS ───────────────────────────────────────────────────────────────
detect_os() {
  case "$(uname -s)" in
    Darwin)                  echo "mac"     ;;
    Linux)                   echo "linux"   ;;
    MINGW*|MSYS*|CYGWIN*)    echo "windows" ;;
    *)                       echo "unknown" ;;
  esac
}

OS=$(detect_os)
info "OS detectado: $OS"
info "Brain dir: $BRAIN_DIR"

# ── Helpers ───────────────────────────────────────────────────────────────────

# Agrega alias a un shell rc file si no existe ya
add_alias_to_file() {
  local rc_file="$1"
  local alias_line="alias brain='bash \"$BRAIN_SCRIPT\"'"

  if [[ ! -f "$rc_file" ]]; then
    warn "$rc_file no existe, creando..."
    touch "$rc_file"
  fi

  if grep -q "alias brain=" "$rc_file" 2>/dev/null; then
    warn "alias 'brain' ya existe en $rc_file — omitiendo."
    return 0
  fi

  echo "" >> "$rc_file"
  echo "# brain-contexts" >> "$rc_file"
  echo "$alias_line" >> "$rc_file"
  ok "Alias agregado en $rc_file"
}

# Detecta qué shells tiene el usuario y agrega el alias a cada uno
install_unix_alias() {
  local added=0

  # Zsh (Mac default desde Catalina, también común en Linux)
  if [[ -f "$HOME/.zshrc" ]] || command -v zsh &>/dev/null; then
    add_alias_to_file "$HOME/.zshrc"
    ((added++))
  fi

  # Bash
  if [[ -f "$HOME/.bashrc" ]]; then
    add_alias_to_file "$HOME/.bashrc"
    ((added++))
  elif [[ -f "$HOME/.bash_profile" ]]; then
    add_alias_to_file "$HOME/.bash_profile"
    ((added++))
  else
    # Si no existe ninguno, crear .bashrc
    add_alias_to_file "$HOME/.bashrc"
    ((added++))
  fi

  if [[ $added -eq 0 ]]; then
    warn "No se detectó ningún shell rc file. Agrega manualmente:"
    echo "  alias brain='bash \"$BRAIN_SCRIPT\"'"
  fi
}

# ── Instalación por OS ────────────────────────────────────────────────────────

install_mac()    { install_unix_alias; }
install_linux()  { install_unix_alias; }

install_windows() {
  # Convertir ruta Unix a Windows para el .bat
  local win_script
  win_script=$(cygpath -w "$BRAIN_SCRIPT" 2>/dev/null || echo "$BRAIN_SCRIPT")

  # Carpeta de scripts del usuario
  local scripts_dir="$HOME/scripts"
  mkdir -p "$scripts_dir"

  local bat_file="$scripts_dir/brain.bat"

  # Crear brain.bat
  cat > "$bat_file" << EOF
@echo off
bash "$win_script" %*
EOF
  ok "Creado: $bat_file"

  # Convertir scripts_dir a ruta Windows
  local win_scripts_dir
  win_scripts_dir=$(cygpath -w "$scripts_dir" 2>/dev/null || echo "$scripts_dir")

  # Agregar al PATH de usuario via PowerShell (no requiere admin)
  local current_path
  current_path=$(powershell.exe -NoProfile -Command \
    '[System.Environment]::GetEnvironmentVariable("PATH","User")' 2>/dev/null || echo "")

  if echo "$current_path" | grep -qi "$(basename "$win_scripts_dir")"; then
    warn "La carpeta ya está en el PATH de usuario — omitiendo."
  else
    powershell.exe -NoProfile -Command "
      \$current = [System.Environment]::GetEnvironmentVariable('PATH','User')
      \$new = \$current + ';$win_scripts_dir'
      [System.Environment]::SetEnvironmentVariable('PATH', \$new, 'User')
    " 2>/dev/null && ok "Carpeta agregada al PATH de usuario: $win_scripts_dir" \
                  || warn "No se pudo modificar el PATH automáticamente. Agrégalo manualmente: $win_scripts_dir"
  fi

  # También agregar alias en Git Bash
  info "Agregando alias en Git Bash también..."
  install_unix_alias
}

# ── Ejecutar ──────────────────────────────────────────────────────────────────
case "$OS" in
  mac)     install_mac     ;;
  linux)   install_linux   ;;
  windows) install_windows ;;
  *)       err "OS no reconocido: $(uname -s)" ;;
esac

echo ""
ok "Instalación completa."
echo ""
echo -e "${BOLD}Para activar en la sesión actual:${NC}"

case "$OS" in
  mac|linux)
    echo "  source ~/.zshrc    # si usas zsh"
    echo "  source ~/.bashrc   # si usas bash"
    ;;
  windows)
    echo "  Abre una nueva terminal (CMD/PowerShell) para que tome efecto el PATH."
    echo "  En Git Bash: source ~/.bashrc"
    ;;
esac

echo ""
echo -e "${BOLD}Uso:${NC}"
echo "  brain              # genera ACTIVE_CONTEXT.md"
echo "  brain claude       # genera contexto + lanza Claude Code"
echo "  brain gemini       # genera contexto + lanza Gemini"
echo "  brain aider        # genera contexto + lanza Aider"