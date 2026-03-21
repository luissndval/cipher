"""
cipher tasks — GitHubIssueSource (F4-2)
Importa issues de GitHub vía API REST (stdlib urllib, sin dependencias externas).

Soporta:
  - URL completa:  https://github.com/owner/repo/issues/123
  - Referencia:    owner/repo#123  o  owner/repo/123
  - Requiere GITHUB_TOKEN en el entorno para repos privados o mayor rate limit.
"""

import json
import os
import re
import urllib.request

from cipher.tasks.sources.base import TicketSource, RawTicket

_URL_PATTERN = re.compile(
    r"github\.com/([^/]+)/([^/]+)/issues/(\d+)"
)
_REF_PATTERN = re.compile(
    r"([^/]+)/([^/#]+)[/#](\d+)"
)


class GitHubIssueSource(TicketSource):

    @property
    def name(self) -> str:
        return "github"

    def fetch(self, ref: str) -> RawTicket:
        owner, repo, number = self._parse_ref(ref)
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
        data = self._request(url)

        title = data.get("title", "")
        body  = data.get("body") or ""
        html_url = data.get("html_url", ref)
        labels = [lbl.get("name", "") for lbl in data.get("labels", [])]

        return RawTicket(
            title=title,
            description=body,
            source="github",
            source_ref=html_url,
            labels=labels,
            extra={
                "number": number,
                "owner": owner,
                "repo": repo,
                "state": data.get("state", ""),
            },
        )

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _parse_ref(self, ref: str) -> tuple[str, str, str]:
        m = _URL_PATTERN.search(ref)
        if m:
            return m.group(1), m.group(2), m.group(3)
        m = _REF_PATTERN.match(ref.strip())
        if m:
            return m.group(1), m.group(2), m.group(3)
        raise ValueError(
            f"Formato de referencia GitHub inválido: '{ref}'\n"
            "  Formatos soportados:\n"
            "    https://github.com/owner/repo/issues/123\n"
            "    owner/repo#123\n"
            "    owner/repo/123"
        )

    def _request(self, url: str) -> dict:
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "cipher-task-engine/0.1")
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise ValueError(f"GitHub API error {e.code}: {body}") from e
        except Exception as e:
            raise ValueError(f"Error al contactar GitHub: {e}") from e
