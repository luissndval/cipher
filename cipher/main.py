#!/usr/bin/env python3
"""
cipher CLI — Punto de entrada principal
Uso: cipher <comando> [opciones]
"""

import sys
import os

# Agregar el directorio padre al path para que los imports del paquete funcionen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cipher import VERSION
from cipher.commands.init import cmd_init
from cipher.commands.update import cmd_update
from cipher.commands.status import cmd_status
from cipher.commands.session import cmd_session

BANNER = f"""
\033[34m╔══════════════════════════════════════════╗
║             cipher  v{VERSION:<19}║
║     Memoria persistente para agentes IA  ║
╚══════════════════════════════════════════╝\033[0m
"""

HELP = """
Comandos:
  cipher init       Onboarding: escanea repos y genera contexto con IA
  cipher claude     Abre sesión de desarrollo con Claude Code
  cipher update     Actualiza contexto después de un cambio
  cipher status     Muestra estado del contexto actual

Ejemplos:
  cd /proyectos/cliente-xyz
  cipher init

  cipher claude

  cipher update
"""


def main():
    if len(sys.argv) < 2:
        print(BANNER)
        print(HELP)
        sys.exit(0)

    if sys.argv[1] in ("--version", "-v"):
        print(f"cipher v{VERSION}")
        sys.exit(0)

    if sys.argv[1] in ("--help", "-h"):
        print(BANNER)
        print(HELP)
        sys.exit(0)

    command = sys.argv[1].lower()
    extra_args = sys.argv[2:]

    if command == "claude":
        cmd_session(agent="claude", args=extra_args)
    elif command == "init":
        cmd_init(args=extra_args)
    elif command == "update":
        cmd_update(args=extra_args)
    elif command == "status":
        cmd_status(args=extra_args)
    else:
        print(f"\033[31m✗ Comando desconocido: {command}\033[0m")
        print("  Comandos disponibles: init, claude, update, status")
        print("  Ejecutá 'cipher --help' para más información.")
        sys.exit(1)


if __name__ == "__main__":
    main()
