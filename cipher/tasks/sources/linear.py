"""
cipher tasks — LinearSource (F4-2)
Importa tickets de Linear vía GraphQL API (stdlib urllib, sin dependencias externas).

Soporta:
  - ID de ticket:  ENG-123  (cualquier prefijo de equipo)
  - URL:           https://linear.app/workspace/issue/ENG-123/título
  - Requiere LINEAR_API_KEY en el entorno.
"""

import json
import os
import re
import urllib.request

from cipher.tasks.sources.base import TicketSource, RawTicket

_LINEAR_API = "https://api.linear.app/graphql"
_ID_PATTERN  = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")
_URL_PATTERN = re.compile(r"linear\.app/[^/]+/issue/([A-Z][A-Z0-9]+-\d+)")

_QUERY = """
query GetIssue($id: String!) {
  issue(id: $id) {
    id
    identifier
    title
    description
    url
    state { name }
    labels { nodes { name } }
    priority
  }
}
"""


class LinearSource(TicketSource):

    @property
    def name(self) -> str:
        return "linear"

    def fetch(self, ref: str) -> RawTicket:
        issue_id = self._parse_ref(ref)
        api_key = os.environ.get("LINEAR_API_KEY", "")
        if not api_key:
            raise ValueError(
                "Se requiere LINEAR_API_KEY en el entorno para importar tickets de Linear."
            )
        data = self._request(issue_id, api_key)
        issue = data.get("data", {}).get("issue")
        if not issue:
            errors = data.get("errors", [])
            msg = errors[0].get("message", "unknown") if errors else "issue not found"
            raise ValueError(f"Linear error para '{issue_id}': {msg}")

        title = issue.get("title", "")
        description = issue.get("description") or ""
        url = issue.get("url", ref)
        labels = [lbl["name"] for lbl in issue.get("labels", {}).get("nodes", [])]

        return RawTicket(
            title=title,
            description=description,
            source="linear",
            source_ref=url,
            labels=labels,
            extra={
                "identifier": issue.get("identifier", issue_id),
                "state": issue.get("state", {}).get("name", ""),
                "priority": issue.get("priority", 0),
            },
        )

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _parse_ref(self, ref: str) -> str:
        m = _URL_PATTERN.search(ref)
        if m:
            return m.group(1)
        m = _ID_PATTERN.search(ref)
        if m:
            return m.group(1)
        raise ValueError(
            f"Formato de referencia Linear inválido: '{ref}'\n"
            "  Formatos soportados:\n"
            "    ENG-123\n"
            "    https://linear.app/workspace/issue/ENG-123/titulo"
        )

    def _request(self, issue_id: str, api_key: str) -> dict:
        payload = json.dumps({
            "query": _QUERY,
            "variables": {"id": issue_id},
        }).encode("utf-8")
        req = urllib.request.Request(
            _LINEAR_API,
            data=payload,
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", api_key)
        req.add_header("User-Agent", "cipher-task-engine/0.1")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise ValueError(f"Linear API error {e.code}: {body}") from e
        except Exception as e:
            raise ValueError(f"Error al contactar Linear: {e}") from e
