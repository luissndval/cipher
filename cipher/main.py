#!/usr/bin/env python3
"""
cipher CLI — Punto de entrada principal
Uso: cipher <comando> [opciones]
"""

import sys
import os



# Fix encoding on Windows consoles (cp1252 → utf-8)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Agregar el directorio padre al path para que los imports del paquete funcionen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cipher import VERSION
from cipher.commands.init import cmd_init
from cipher.commands.update import cmd_update
from cipher.commands.status import cmd_status
from cipher.commands.session import cmd_session
from cipher.commands.index import cmd_index
from cipher.commands.impact import cmd_impact
from cipher.commands.pack import cmd_pack
from cipher.commands.task import cmd_task
from cipher.commands.audit import cmd_audit

BANNER = f"""
\033[34m╔══════════════════════════════════════════╗
║           cipheria  v{VERSION:<18}║
║     Memoria persistente para agentes IA  ║
╚══════════════════════════════════════════╝\033[0m
"""

HELP = """
Comandos:
  cipheria init       Onboarding: escanea repos y genera contexto con IA
  cipheria claude     Abre sesión de desarrollo con Claude Code
  cipheria update     Actualiza contexto después de un cambio
  cipheria status     Muestra estado del contexto actual
  cipheria index      Genera índice estructural del repo (sin LLM)
  cipheria impact     Muestra qué archivos se ven afectados por un cambio
  cipheria pack       Genera el context pack mínimo para una tarea
  cipheria task       Crea una task, genera intent y lanza el agente
  cipheria audit      Historial de auditoría de sesiones IA

Ejemplos:
  cd /proyectos/cliente-xyz
  cipheria init

  cipheria claude

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
    elif command == "index":
        cmd_index(args=extra_args)
    elif command == "impact":
        cmd_impact(args=extra_args)
    elif command == "pack":
        cmd_pack(args=extra_args)
    elif command == "task":
        cmd_task(args=extra_args)
    elif command == "audit":
        cmd_audit(args=extra_args)
    else:
        print(f"\033[31m✗ Comando desconocido: {command}\033[0m")
        print("  Comandos disponibles: init, claude, update, status")
        print("  Ejecutá 'cipher --help' para más información.")
        sys.exit(1)


if __name__ == "__main__":
    main()
