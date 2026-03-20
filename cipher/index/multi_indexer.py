"""
cipher index — MultiRepoIndexer
Orquesta la indexación incremental de todos los repos de un cliente.
"""

import os
import subprocess

from cipher.index.indexer import RepoIndexer
from cipher.index.schema import RepoIndex
from cipher.core.paths import resolve_repo_path

YELLOW = "\033[1;33m"
RED    = "\033[0;31m"
GREEN  = "\033[0;32m"
CYAN   = "\033[0;36m"
NC     = "\033[0m"


class MultiRepoIndexer:
    def __init__(self, cipher_dir: str):
        """
        cipher_dir: directorio raíz donde vive cipher (contiene .cipher/).
        Los índices se guardan en cipher_dir/.cipher/index/<repo_key>/.
        """
        self.cipher_dir = cipher_dir

    def index_client_repos(
        self,
        client_name: str,
        config: dict,
    ) -> dict:
        """
        Para cada repo del cliente en config:
          1. Verifica que el path local existe.
          2. Si no existe: loguea warning + pregunta git URL.
             - Si el usuario provee URL: clona el repo y continúa.
             - Si no: omite ese repo.
          3. Ejecuta indexación incremental (SHA-256).
          4. Retorna dict {repo_key: RepoIndex}.
        """
        client_data = config.get("clients", {}).get(client_name, {})
        repos = client_data.get("repos", {})

        results: dict[str, RepoIndex] = {}

        if not repos:
            print(f"  {YELLOW}⚠ Cliente '{client_name}' no tiene repos registrados.{NC}")
            return results

        print(f"  Indexando repos del cliente {CYAN}{client_name}{NC} ({len(repos)} repo(s))...")

        for repo_key, repo_info in repos.items():
            if not isinstance(repo_info, dict):
                continue

            repo_name = repo_info.get("name") or repo_key
            repo_path = resolve_repo_path(client_data, repo_key, repo_info)

            if not repo_path:
                print(f"  {YELLOW}⚠ [{repo_key}] Sin path configurado — omitido.{NC}")
                continue

            # Verificar existencia del path local
            if not os.path.isdir(repo_path):
                print(f"  {YELLOW}⚠ [{repo_key}] Path no encontrado: {repo_path}{NC}")
                repo_path = self._prompt_clone(repo_key, repo_path)
                if not repo_path:
                    print(f"  {YELLOW}  → Omitiendo {repo_key}.{NC}")
                    continue

            # Determinar directorio de índice
            index_dir = os.path.join(self.cipher_dir, ".cipher", "index", repo_key)
            index_path = os.path.join(index_dir, "index.json")

            # Cargar índice existente para re-indexación incremental
            existing_index = None
            if os.path.exists(index_path):
                try:
                    existing_index = RepoIndexer.load(index_path)
                except Exception:
                    existing_index = None

            # Indexar
            try:
                indexer = RepoIndexer(repo_path, repo_name)
                repo_index = indexer.index(existing_index=existing_index)
                indexer.save(repo_index, index_dir)

                reused = sum(
                    1 for f in repo_index.files
                    if existing_index and any(
                        ef.path == f.path and ef.content_hash == f.content_hash
                        for ef in existing_index.files
                    )
                )
                total = repo_index.stats.total_files
                print(
                    f"  {GREEN}✓{NC} [{repo_key}] {total} archivos "
                    f"({reused} sin cambios, {total - reused} re-indexados)"
                )
                results[repo_key] = repo_index

            except Exception as e:
                print(f"  {RED}✗ [{repo_key}] Error al indexar: {e}{NC}")
                continue

        return results

    @staticmethod
    def _prompt_clone(repo_key: str, original_path: str) -> str | None:
        """
        Pregunta al usuario si desea proveer una git URL para clonar el repo.
        Retorna el path donde se clonó, o None si el usuario no provee URL.
        """
        try:
            git_url = input(
                f"  ¿URL git para clonar '{repo_key}'? "
                f"(Enter para omitir): "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            return None

        if not git_url:
            return None

        clone_path = original_path
        print(f"  Clonando {git_url} → {clone_path} ...")
        try:
            result = subprocess.run(
                ["git", "clone", git_url, clone_path],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"  {GREEN}✓ Clonado exitosamente.{NC}")
                return clone_path
            else:
                print(f"  {RED}✗ Error al clonar: {result.stderr.strip()}{NC}")
                return None
        except Exception as e:
            print(f"  {RED}✗ Error al clonar: {e}{NC}")
            return None
