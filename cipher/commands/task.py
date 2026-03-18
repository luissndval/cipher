"""
cipher task — Task Engine (F4-5)
Crea una task formalizada, genera intent, construye context pack y lanza el agente.

Uso:
  cipher task "descripción libre"
  cipher task "título: descripción detallada"
  cipher task --from-gh owner/repo#123
  cipher task --from-linear ENG-456
  cipher task "descripción" --dry-run     (genera intent sin lanzar agente)
  cipher task --list [--status PENDING]
"""

import os
import uuid
from datetime import datetime, timezone

from cipher.core.loader import ContextLoader
from cipher.tasks.schema import Task, TaskType, TaskStatus
from cipher.tasks.store import TaskStore
from cipher.tasks.analyzer import TaskAnalyzer
from cipher.tasks.sources.manual import ManualSource
from cipher.index.indexer import RepoIndexer
from cipher.index.multi_indexer import MultiRepoIndexer
from cipher.graph.builder import GraphBuilder
from cipher.graph.merger import GraphMerger
from cipher.pack.builder import PackBuilder
from cipher.audit.writer import AuditWriter

GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
RED    = '\033[0;31m'
BLUE   = '\033[0;34m'
CYAN   = '\033[0;36m'
NC     = '\033[0m'


def cmd_task(args: list):
    # ── Parsear argumentos ──────────────────────────────────────────────────
    description = ""
    from_gh      = None
    from_linear  = None
    repo_name    = None
    provider     = "claude"
    dry_run      = False
    list_mode    = False
    list_status  = None

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--from-gh" and i + 1 < len(args):
            from_gh = args[i + 1]; i += 2
        elif a.startswith("--from-gh="):
            from_gh = a.split("=", 1)[1]; i += 1
        elif a == "--from-linear" and i + 1 < len(args):
            from_linear = args[i + 1]; i += 2
        elif a.startswith("--from-linear="):
            from_linear = a.split("=", 1)[1]; i += 1
        elif a == "--repo" and i + 1 < len(args):
            repo_name = args[i + 1]; i += 2
        elif a.startswith("--repo="):
            repo_name = a.split("=", 1)[1]; i += 1
        elif a == "--provider" and i + 1 < len(args):
            provider = args[i + 1]; i += 2
        elif a.startswith("--provider="):
            provider = a.split("=", 1)[1]; i += 1
        elif a == "--dry-run":
            dry_run = True; i += 1
        elif a == "--list":
            list_mode = True; i += 1
        elif a == "--status" and i + 1 < len(args):
            list_status = args[i + 1].upper(); i += 2
        elif not a.startswith("--"):
            description += (" " if description else "") + a; i += 1
        else:
            i += 1

    try:
        loader = ContextLoader()
    except FileNotFoundError as e:
        print(str(e))
        return

    store = TaskStore(loader.cipher_dir)

    # ── Modo lista ──────────────────────────────────────────────────────────
    if list_mode:
        _cmd_list(store, list_status)
        return

    # ── Obtener ticket ──────────────────────────────────────────────────────
    print(f"\n{BLUE}╔══════════════════════════════════════════╗")
    print(f"║          cipher task                      ║")
    print(f"╚══════════════════════════════════════════╝{NC}\n")

    raw = _fetch_ticket(from_gh, from_linear, description)
    if raw is None:
        print(f"{RED}Uso: cipher task <descripción> | --from-gh <ref> | --from-linear <id>{NC}")
        return

    print(f"  Título  : {raw.title}")
    if raw.description:
        snippet = raw.description[:80].replace("\n", " ")
        print(f"  Desc    : {snippet}{'...' if len(raw.description) > 80 else ''}")
    if raw.source_ref:
        print(f"  Origen  : {raw.source_ref}")
    print()

    # ── Resolver repo ───────────────────────────────────────────────────────
    repo_path, resolved_name, client_name = _resolve_repo(loader, repo_name)
    if not repo_path:
        print(f"{RED}✗ No se pudo detectar el repo. Usá --repo <nombre>.{NC}")
        return

    if not resolved_name:
        resolved_name = os.path.basename(repo_path)
    if not client_name:
        client_name = "_"

    print(f"  Repo    : {CYAN}{resolved_name}{NC}  Cliente: {client_name}")
    print(f"  Provider: {provider}\n")

    # ── Indexar todos los repos del cliente (incremental) ──────────────────
    print(f"  {YELLOW}▸ Indexando repos del cliente '{client_name}'...{NC}")
    all_indices = _index_client_repos(loader, client_name, repo_path, resolved_name)
    if not all_indices:
        print(f"  {RED}✗ No se pudo indexar ningún repo.{NC}")
        return

    # Repo actual — usado para PackBuilder y TaskAnalyzer
    repo_index = all_indices.get(resolved_name)
    if repo_index is None:
        print(f"  {RED}✗ No se pudo indexar el repo actual ({resolved_name}).{NC}")
        return

    # ── Construir grafos individuales y merge en memoria ───────────────────
    print(f"  {YELLOW}▸ Construyendo grafos de dependencias...{NC}")
    all_graphs, graph = _build_graphs(loader, all_indices, resolved_name)

    # Grafo merged (cross-repo, solo en memoria) — usado en F6
    merged_graph = GraphMerger().merge(all_graphs) if len(all_graphs) > 1 else graph
    print(f"  {GREEN}✓{NC} {len(all_graphs)} grafo(s) — "
          f"{merged_graph.node_count} nodos, {merged_graph.edge_count} aristas (merged)\n")

    # ── Crear Task ──────────────────────────────────────────────────────────
    task_id = str(uuid.uuid4())[:8]
    analyzer = TaskAnalyzer(repo_index, graph)
    task_type = analyzer.detect_type(raw.title, raw.description)

    task = Task(
        task_id=task_id,
        type=task_type,
        title=raw.title,
        description=raw.description,
        repo=resolved_name,
        client=client_name,
        status=TaskStatus.PENDING.value,
        created_at=datetime.now(timezone.utc).isoformat(),
        source=raw.source,
        source_ref=raw.source_ref,
        target_files=[],
        context_pack_id="",
        intent_path="",
    )
    store.save_task(task)
    audit = AuditWriter(loader.cipher_dir)
    print(f"  {GREEN}✓{NC} Task creada: {CYAN}{task_id}{NC}  [{task_type}]\n")

    # ── Construir Context Pack ──────────────────────────────────────────────
    print(f"  {YELLOW}▸ Construyendo context pack...{NC}")
    packs_dir = os.path.join(loader.cipher_dir, ".cipher", "packs", resolved_name)
    pack_builder = PackBuilder(
        repo_index=repo_index,
        graph=graph,
        repo_path=repo_path,
        cipher_dir=loader.cipher_dir,
        client_name=client_name,
    )
    full_text = f"{raw.title} {raw.description}"
    pack = pack_builder.build(full_text, provider=provider, task_id=task_id)
    md_path, _ = PackBuilder.save(pack, packs_dir)

    task.context_pack_id = task_id
    task.target_files = [e.path for e in pack.entries if e.role == "target"]

    m = pack.manifest
    pct = 100 * m.tokens_used // m.token_budget if m.token_budget else 0
    print(f"  {GREEN}✓{NC} Pack: {len(task.target_files)} targets, "
          f"{sum(1 for e in pack.entries if e.role=='dependency')} deps, "
          f"{m.tokens_used:,}/{m.token_budget:,}t ({pct}%)\n")

    # ── Generar y guardar ContextManifest (F5-2) ────────────────────────────
    context_manifest = audit.build_manifest(m, event="task_run", task_id=task_id)
    manifest_path = audit.save_manifest(context_manifest, client_name, resolved_name, task_id)
    audit.append_entry(context_manifest)
    print(f"  {GREEN}✓{NC} Manifest: {manifest_path}\n")

    # ── Generar Alert de impacto con Gemini (usa grafo merged) ────────────
    print(f"  {YELLOW}▸ Analizando impacto con Gemini...{NC}")
    try:
        from cipher.analysis.providers import get_analysis_provider
        from cipher.alerts.generator import AlertGenerator

        gemini = get_analysis_provider("gemini")
        if gemini.can_analyze():
            # Impact set usando el grafo merged (cross-repo).
            # Los paths en merged_graph están prefijados con repo_key::.
            # Construimos el prefijo del repo actual para consultar el grafo merged.
            current_prefix = resolved_name + "::"
            all_impact: dict = {}
            for target in task.target_files:
                prefixed_target = current_prefix + target
                for entry in merged_graph.impact_set(prefixed_target, max_depth=10):
                    if entry.file_path not in all_impact:
                        all_impact[entry.file_path] = entry
                # Fallback: también consultar el grafo individual del repo actual
                for entry in graph.impact_set(target, max_depth=10):
                    key = entry.file_path
                    if key not in all_impact:
                        all_impact[key] = entry
            impact_list = sorted(all_impact.values(), key=lambda e: (e.depth, e.file_path))

            alert_gen = AlertGenerator(
                task=task,
                impact_entries=impact_list,
                repo_path=repo_path,
                client_name=client_name,
                cipher_dir=loader.cipher_dir,
                config=loader.config,
            )
            alert_path = alert_gen.generate(gemini)
            print(f"  {GREEN}✓{NC} Alert: {CYAN}{alert_path}{NC}\n")
        else:
            print(f"  {YELLOW}⚠ Gemini no configurado — alert omitido{NC}\n")
    except Exception as e:
        print(f"  {YELLOW}⚠ Alert no generado: {e}{NC}\n")

    # ── Generar TaskIntent ──────────────────────────────────────────────────
    print(f"  {YELLOW}▸ Generando task intent...{NC}")
    intent = analyzer.build_intent(task, context_pack_path=md_path)
    intent_path = store.save_intent(intent, client_name, resolved_name)
    task.intent_path = intent_path
    store.save_task(task)

    print(f"  {GREEN}✓{NC} Intent: {len(intent.files_to_modify)} archivos a modificar")
    if intent.constraints:
        print(f"  {YELLOW}⚠ Restricciones detectadas: {', '.join(intent.constraints)}{NC}")

    print(f"\n{'─' * 50}")
    print(f"\n  {BLUE}RESUMEN{NC}\n")
    print(f"  Task ID : {task_id}")
    print(f"  Tipo    : {task_type}")
    print(f"  Pack    : {md_path}")
    print(f"  Intent  : {intent_path}")

    if intent.files_to_modify:
        print(f"\n  Archivos a modificar:")
        for f in intent.files_to_modify:
            print(f"    {CYAN}{f}{NC}")

    if dry_run:
        print(f"\n  {YELLOW}(dry-run — agente no lanzado){NC}")
        _print_pr_preview(context_manifest)
        return

    # ── Lanzar agente ───────────────────────────────────────────────────────
    print(f"\n  {YELLOW}▸ Lanzando agente...{NC}\n")
    store.update_status(task, TaskStatus.IN_PROGRESS.value)
    try:
        from cipher.agents.launcher import launch_agent
        launch_agent("claude", md_path, intent_path, repo_path)
        store.update_status(task, TaskStatus.DONE.value)
        audit.update_entry(context_manifest.manifest_id, result="done")
        audit.update_manifest(context_manifest, result="done")
        print(f"\n  {GREEN}✓ Sesión completada — task {task_id} marcada como DONE{NC}\n")
    except Exception as e:
        store.update_status(task, TaskStatus.FAILED.value)
        audit.update_entry(context_manifest.manifest_id, result="failed")
        audit.update_manifest(context_manifest, result="failed")
        print(f"\n  {RED}✗ Error al lanzar agente: {e}{NC}\n")


# ─── Modo lista ────────────────────────────────────────────────────────────────

def _cmd_list(store: TaskStore, status: str | None):
    tasks = store.list_tasks(status=status)
    if not tasks:
        label = f" con status {status}" if status else ""
        print(f"{YELLOW}No hay tasks registradas{label}.{NC}")
        return

    print(f"\n  {BLUE}Tasks registradas{NC}  ({len(tasks)} total)\n")
    for t in tasks:
        status_color = {
            "PENDING":     YELLOW,
            "IN_PROGRESS": CYAN,
            "DONE":        GREEN,
            "FAILED":      RED,
        }.get(t.status, NC)
        print(f"  [{status_color}{t.status:11}{NC}] {CYAN}{t.task_id}{NC}  "
              f"[{t.type:7}]  {t.title[:60]}")
    print()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _print_pr_preview(manifest):
    from cipher.audit.pr_comment import generate_pr_comment
    print(f"\n  --- PR Comment Preview ---")
    print(generate_pr_comment(manifest))


def _fetch_ticket(from_gh, from_linear, description):
    if from_gh:
        try:
            from cipher.tasks.sources.github import GitHubIssueSource
            return GitHubIssueSource().fetch(from_gh)
        except ValueError as e:
            print(f"{RED}✗ {e}{NC}")
            return None
    if from_linear:
        try:
            from cipher.tasks.sources.linear import LinearSource
            return LinearSource().fetch(from_linear)
        except ValueError as e:
            print(f"{RED}✗ {e}{NC}")
            return None
    if description:
        return ManualSource().fetch(description)
    return None


def _resolve_repo(loader, repo_name_hint):
    cwd = os.getcwd().replace("\\", "/")
    config = loader.config
    for client_name, client_data in config.get("clients", {}).items():
        if not isinstance(client_data, dict):
            continue
        for rname, rinfo in client_data.get("repos", {}).items():
            if not isinstance(rinfo, dict):
                continue
            rpath = rinfo.get("path", "").replace("\\", "/")
            if not rpath:
                continue
            if cwd.startswith(rpath):
                return rpath, rname, client_name
            if repo_name_hint and rname == repo_name_hint:
                return rpath, rname, client_name
    if not config.get("clients"):
        return os.getcwd(), os.path.basename(os.getcwd()), None
    return None, None, None


def _index_client_repos(loader, client_name: str, current_repo_path: str, current_repo_name: str) -> dict:
    """
    Indexa todos los repos del cliente usando MultiRepoIndexer (incremental).
    Si el cliente no tiene repos registrados o el repo actual no está en config,
    indexa únicamente el repo actual como fallback.
    Retorna dict {repo_key: RepoIndex}.
    """
    multi = MultiRepoIndexer(loader.cipher_dir)
    results = multi.index_client_repos(client_name, loader.config)

    # Fallback: si el repo actual no está en los resultados, indexarlo directamente
    if current_repo_name not in results:
        index_dir  = os.path.join(loader.cipher_dir, ".cipher", "index", current_repo_name)
        index_path = os.path.join(index_dir, "index.json")

        existing_index = None
        if os.path.exists(index_path):
            try:
                existing_index = RepoIndexer.load(index_path)
            except Exception:
                pass

        try:
            indexer = RepoIndexer(current_repo_path, current_repo_name)
            repo_index = indexer.index(existing_index=existing_index)
            indexer.save(repo_index, index_dir)
            results[current_repo_name] = repo_index
            print(f"  {GREEN}✓{NC} [{current_repo_name}] {repo_index.stats.total_files} archivos indexados")
        except Exception as e:
            print(f"  {RED}✗ Error al indexar repo actual: {e}{NC}")

    return results


def _build_graphs(loader, all_indices: dict, current_repo_name: str) -> tuple:
    """
    Construye un DependencyGraph por cada RepoIndex en all_indices.
    Persiste cada grafo individual en disco (fuente de verdad).
    Retorna (dict{repo_key: DependencyGraph}, current_graph).
    """
    all_graphs = {}

    for repo_key, repo_index in all_indices.items():
        index_dir  = os.path.join(loader.cipher_dir, ".cipher", "index", repo_key)
        graph_path = os.path.join(index_dir, "graph.json")
        try:
            graph = GraphBuilder(repo_index).build()
            GraphBuilder.save(graph, index_dir)
            all_graphs[repo_key] = graph
        except Exception as e:
            print(f"  {YELLOW}⚠ [{repo_key}] Error al construir grafo: {e}{NC}")
            # Intentar cargar grafo previo desde disco
            if os.path.exists(graph_path):
                try:
                    all_graphs[repo_key] = GraphBuilder.load(graph_path)
                except Exception:
                    pass

    current_graph = all_graphs.get(current_repo_name)

    # Fallback extremo: si no tenemos grafo del repo actual, construirlo
    if current_graph is None and current_repo_name in all_indices:
        try:
            current_graph = GraphBuilder(all_indices[current_repo_name]).build()
        except Exception:
            pass

    return all_graphs, current_graph
