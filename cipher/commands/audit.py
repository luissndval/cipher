"""
cipher audit — Sistema de auditoría de sesiones IA (F5-5)
Muestra el historial de cambios generados por la IA.

Uso:
  cipher audit                          lista todas las entradas
  cipher audit <task_id>                detalle de una task específica
  cipher audit --repo <nombre>          filtrar por repo
  cipher audit --client <nombre>        filtrar por cliente
  cipher audit --since <YYYY-MM>        filtrar desde fecha
  cipher audit --result <pending|done|failed>
  cipher audit --pr <task_id> <pr_url>  registrar URL de PR en el manifest
  cipher audit --stats                  estadísticas globales
"""

import os

from cipher.core.loader import ContextLoader
from cipher.audit.reader import AuditReader
from cipher.audit.writer import AuditWriter
from cipher.audit.pr_comment import generate_pr_comment

GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
RED    = '\033[0;31m'
BLUE   = '\033[0;34m'
CYAN   = '\033[0;36m'
NC     = '\033[0m'

_RESULT_COLOR = {
    "pending": YELLOW,
    "done":    GREEN,
    "failed":  RED,
}
_EVENT_LABEL = {
    "task_run":      "task",
    "session_start": "session",
}


def cmd_audit(args: list):
    task_id_arg = None
    repo        = None
    client      = None
    since       = None
    result_f    = None
    pr_task_id  = None
    pr_url      = None
    show_stats  = False
    limit       = 50

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--repo" and i + 1 < len(args):
            repo = args[i + 1]; i += 2
        elif a.startswith("--repo="):
            repo = a.split("=", 1)[1]; i += 1
        elif a == "--client" and i + 1 < len(args):
            client = args[i + 1]; i += 2
        elif a.startswith("--client="):
            client = a.split("=", 1)[1]; i += 1
        elif a == "--since" and i + 1 < len(args):
            since = args[i + 1]; i += 2
        elif a.startswith("--since="):
            since = a.split("=", 1)[1]; i += 1
        elif a == "--result" and i + 1 < len(args):
            result_f = args[i + 1].lower(); i += 2
        elif a.startswith("--result="):
            result_f = a.split("=", 1)[1].lower(); i += 1
        elif a == "--pr" and i + 2 < len(args):
            pr_task_id = args[i + 1]; pr_url = args[i + 2]; i += 3
        elif a == "--stats":
            show_stats = True; i += 1
        elif a == "--limit" and i + 1 < len(args):
            try:
                limit = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif not a.startswith("--"):
            task_id_arg = a; i += 1
        else:
            i += 1

    try:
        loader = ContextLoader()
    except FileNotFoundError as e:
        print(str(e))
        return

    reader = AuditReader(loader.cipher_dir)
    writer = AuditWriter(loader.cipher_dir)

    # ── Registrar PR URL ─────────────────────────────────────────────────────
    if pr_task_id and pr_url:
        _register_pr(reader, writer, pr_task_id, pr_url)
        return

    # ── Estadísticas ─────────────────────────────────────────────────────────
    if show_stats:
        _show_stats(reader)
        return

    # ── Detalle de una task ───────────────────────────────────────────────────
    if task_id_arg:
        _show_detail(reader, task_id_arg)
        return

    # ── Lista ─────────────────────────────────────────────────────────────────
    entries = reader.entries(
        repo=repo, client=client, since=since,
        result=result_f, limit=limit,
    )

    print(f"\n{BLUE}╔══════════════════════════════════════════╗")
    print(f"║        cipheria audit                     ║")
    print(f"╚══════════════════════════════════════════╝{NC}\n")

    if not entries:
        print(f"  {YELLOW}No hay entradas en el audit log.{NC}\n")
        return

    print(f"  {len(entries)} entrada(s)  {_active_filters(repo, client, since, result_f)}\n")
    print(f"  {'TIMESTAMP':<26}  {'TASK':>8}  {'REPO':<18}  {'TOKENS':>8}  {'RESULT'}")
    print(f"  {'─'*26}  {'─'*8}  {'─'*18}  {'─'*8}  {'─'*8}")

    for e in entries:
        ts = e.timestamp[:19].replace("T", " ")
        rc = _RESULT_COLOR.get(e.result, NC)
        ev = _EVENT_LABEL.get(e.event, e.event)
        print(f"  {ts}  {CYAN}{e.task_id:>8}{NC}  {e.repo:<18}  "
              f"{e.tokens_used:>8,}  {rc}{e.result}{NC}")
    print()


# ─── Helpers de visualización ─────────────────────────────────────────────────

def _show_detail(reader: AuditReader, task_id: str):
    manifest = reader.find_manifest(task_id)
    if not manifest:
        print(f"{RED}✗ No se encontró manifest para task '{task_id}'.{NC}")
        return

    print(f"\n{BLUE}── Manifest: {task_id} ──{NC}\n")
    print(f"  Evento   : {manifest.event}")
    print(f"  Modelo   : {manifest.model}")
    print(f"  Repo     : {manifest.repo}  /  Cliente: {manifest.client}")
    print(f"  Timestamp: {manifest.timestamp}")
    rc = _RESULT_COLOR.get(manifest.result, NC)
    print(f"  Resultado: {rc}{manifest.result}{NC}")
    print(f"  Budget   : {manifest.tokens_used:,} / {manifest.token_budget:,}t "
          f"({manifest.budget_pct}%)")
    if manifest.pr_url:
        print(f"  PR       : {manifest.pr_url}")

    print(f"\n  {BLUE}Archivos ({manifest.files_count}){NC}")
    for f in manifest.files_used:
        role = f.get("role", "")
        path = f.get("path", "")
        tokens = f.get("tokens", 0)
        print(f"    [{role:10}] {CYAN}{path}{NC}  (~{tokens:,}t)")

    if manifest.dependencies_included:
        print(f"\n  {BLUE}Dependencias expandidas{NC}")
        for dep in manifest.dependencies_included:
            print(f"    {dep}")

    if manifest.rules_applied:
        print(f"\n  {BLUE}Reglas aplicadas{NC}")
        for rule in manifest.rules_applied:
            print(f"    - {rule}")

    print(f"\n  {YELLOW}── PR Comment Preview ──{NC}")
    print(generate_pr_comment(manifest))


def _show_stats(reader: AuditReader):
    s = reader.stats()
    print(f"\n{BLUE}── cipheria audit stats ──{NC}\n")
    if not s["total"]:
        print(f"  {YELLOW}Audit log vacío.{NC}\n")
        return
    print(f"  Total sesiones  : {s['total']}")
    print(f"  Tokens usados   : {s['total_tokens_used']:,}")
    print(f"  Última actividad: {s['latest'][:19].replace('T', ' ')}\n")
    if s.get("by_result"):
        print(f"  {BLUE}Por resultado:{NC}")
        for result, count in sorted(s["by_result"].items()):
            rc = _RESULT_COLOR.get(result, NC)
            print(f"    {rc}{result:10}{NC} : {count}")
    if s.get("by_repo"):
        print(f"\n  {BLUE}Por repo:{NC}")
        for repo, count in sorted(s["by_repo"].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"    {CYAN}{repo:<20}{NC} : {count}")
    print()


def _register_pr(reader: AuditReader, writer: AuditWriter, task_id: str, pr_url: str):
    manifest = reader.find_manifest(task_id)
    if not manifest:
        print(f"{RED}✗ No se encontró manifest para task '{task_id}'.{NC}")
        return
    writer.update_manifest(manifest, pr_url=pr_url, result="done")
    writer.update_entry(manifest.manifest_id, pr_url=pr_url, result="done")
    print(f"{GREEN}✓ PR registrado: {task_id} → {pr_url}{NC}")


def _active_filters(*filters) -> str:
    labels = [str(f) for f in filters if f]
    return f"(filtros: {', '.join(labels)})" if labels else ""
