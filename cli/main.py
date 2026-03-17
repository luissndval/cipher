#!/usr/bin/env python3
"""
cipher CLI — Punto de entrada principal
Uso: cipher <comando> [opciones]
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from commands.init import cmd_init
from commands.update import cmd_update
from commands.status import cmd_status
from commands.session import cmd_session

VERSION = "1.0.0"

BANNER = """
\033[34m╔══════════════════════════════════════════╗
║             cipher                       ║
║     Memoria persistente para agentes IA  ║
╚══════════════════════════════════════════╝\033[0m
"""

HELP = """
Comandos:
  cipher init       Onboarding: escanea repos y genera contexto con Gemini
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
