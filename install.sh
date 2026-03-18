#!/usr/bin/env bash
# =============================================================================
# cipher — install.sh
# Instala cipher como comando global
# =============================================================================

set -e

CIPHER_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_LOCAL="$CIPHER_DIR/.cipher/config.local.json"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         cipher — Instalación             ║${NC}"
echo -e "${BLUE}║   Memoria persistente para agentes IA    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# -----------------------------------------------------------------------------
# 1. Verificar dependencias base
# -----------------------------------------------------------------------------
echo -e "${YELLOW}▸ Verificando dependencias base...${NC}"

if ! command -v python3 &>/dev/null; then
  echo -e "${RED}✗ Python3 no encontrado. Instalalo desde https://python.org${NC}"
  exit 1
fi
echo -e "${GREEN}  ✓ Python3: $(python3 --version)${NC}"

PIP=$(command -v pip3 2>/dev/null || command -v pip 2>/dev/null)
if [ -z "$PIP" ]; then
  echo -e "${RED}✗ pip no encontrado.${NC}"
  exit 1
fi
echo -e "${GREEN}  ✓ pip: $($PIP --version | cut -d' ' -f1-2)${NC}"

if ! command -v git &>/dev/null; then
  echo -e "${RED}✗ git no encontrado.${NC}"
  exit 1
fi
echo -e "${GREEN}  ✓ git: $(git --version)${NC}"

# -----------------------------------------------------------------------------
# 2. Instalar dependencias Python del CLI
# -----------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}▸ Instalando dependencias Python...${NC}"
$PIP install -q -r "$CIPHER_DIR/requirements.txt"
echo -e "${GREEN}  ✓ Dependencias instaladas${NC}"

# -----------------------------------------------------------------------------
# 3. Verificar Claude Code (agente de codificación)
# -----------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}▸ Verificando Claude Code...${NC}"

if command -v claude &>/dev/null; then
  echo -e "${GREEN}  ✓ Claude Code ya instalado${NC}"
elif command -v npm &>/dev/null; then
  echo -e "  Instalando Claude Code..."
  npm install -g @anthropic-ai/claude-code &>/dev/null && \
    echo -e "${GREEN}  ✓ Claude Code instalado${NC}" || \
    echo -e "${YELLOW}  ⚠ Claude Code — falló. Instalalo manualmente: npm install -g @anthropic-ai/claude-code${NC}"
else
  echo -e "${YELLOW}  ⚠ Claude Code requiere npm — instalalo en https://nodejs.org${NC}"
fi

# -----------------------------------------------------------------------------
# 4. Registrar comando global cipher
# -----------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}▸ Registrando comando global cipher...${NC}"

mkdir -p "$CIPHER_DIR/bin"
cat > "$CIPHER_DIR/bin/cipher" << EOF
#!/usr/bin/env bash
export CIPHER_PATH="$CIPHER_DIR"
python3 "$CIPHER_DIR/cipher/main.py" "\$@"
EOF
chmod +x "$CIPHER_DIR/bin/cipher"

SHELL_RC=""
if [ -f "$HOME/.zshrc" ]; then
  SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
  SHELL_RC="$HOME/.bashrc"
elif [ -f "$HOME/.bash_profile" ]; then
  SHELL_RC="$HOME/.bash_profile"
fi

EXPORT_LINE="export PATH=\"$CIPHER_DIR/bin:\$PATH\""
if [ -n "$SHELL_RC" ]; then
  if ! grep -q "cipher/bin" "$SHELL_RC"; then
    echo "" >> "$SHELL_RC"
    echo "# cipher CLI" >> "$SHELL_RC"
    echo "$EXPORT_LINE" >> "$SHELL_RC"
    echo -e "${GREEN}  ✓ PATH actualizado en $SHELL_RC${NC}"
  else
    echo -e "${GREEN}  ✓ PATH ya configurado${NC}"
  fi
fi

export PATH="$CIPHER_DIR/bin:$PATH"

# -----------------------------------------------------------------------------
# 5. Crear config.local.json si no existe
# -----------------------------------------------------------------------------
echo ""
if [ ! -f "$CONFIG_LOCAL" ]; then
  cp "$CIPHER_DIR/.cipher/config.local.example.json" "$CONFIG_LOCAL" 2>/dev/null || \
    echo '{"anthropic":{"api_key":"","model":"claude-sonnet-4-6"},"google":{"api_key":"","model":"gemini-2.5-flash"}}' > "$CONFIG_LOCAL"
  echo -e "${GREEN}  ✓ config.local.json creado${NC}"
else
  echo -e "${GREEN}  ✓ config.local.json ya existe${NC}"
fi

# -----------------------------------------------------------------------------
# 6. Resumen final
# -----------------------------------------------------------------------------
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          ✓ Instalación completa          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Reiniciá tu terminal o ejecutá:"
echo -e "  ${YELLOW}source $SHELL_RC${NC}"
echo ""
echo -e "  Luego posicionante en la carpeta de tu proyecto:"
echo -e "  ${YELLOW}cipher init${NC}       — registra el proyecto y genera contexto con Gemini"
echo -e "  ${YELLOW}cipher claude${NC}     — abre sesión de desarrollo con Claude Code"
echo -e "  ${YELLOW}cipher update${NC}     — actualiza contexto tras un cambio"
echo -e "  ${YELLOW}cipher status${NC}     — estado del contexto actual"
echo ""
echo -e "  ${BLUE}ℹ Configurá tus API keys en .cipher/config.local.json${NC}"
echo ""
