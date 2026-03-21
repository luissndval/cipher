"""
cipher analysis — Providers

Dos roles:
  - AnalysisProvider : analiza repos y genera contexto (Gemini por defecto)
  - CodingAgent      : agente de codificación interactivo (Claude Code)

Para agregar un provider:
  1. Implementar analyze_repo() y analyze_diff() (análisis)
     o chat() e is_configured() (coding agent).
  2. Registrarlo en get_analysis_provider().
"""

from cipher.core.config import load_config, save_provider_config  # noqa: F401 (re-exported)


def get_analysis_provider(preferred: str = "gemini"):
    """Provider para análisis de repos (cipher init, cipher update). Default: Gemini."""
    cfg = load_config()
    if preferred == "gemini":
        p = cfg["google"]
        return GeminiProvider(api_key=p["api_key"], model=p["model"])
    if preferred == "claude":
        p = cfg["anthropic"]
        return ClaudeProvider(api_key=p["api_key"], auth_mode=p["auth"], model=p["model"])
    raise ValueError(f"Provider de análisis desconocido: {preferred}")


def get_coding_agent():
    """Agente de codificación interactivo (cipher claude)."""
    cfg = load_config()
    p = cfg["anthropic"]
    return ClaudeProvider(api_key=p["api_key"], auth_mode=p["auth"], model=p["model"])


# ─── CLAUDE ───────────────────────────────────────────────────────────────────

class ClaudeProvider:
    name = "Claude (Anthropic)"
    max_context_chars = 60_000
    DEFAULT_MODEL = "claude-sonnet-4-6"

    def __init__(self, api_key: str, auth_mode: str = "none", model: str = ""):
        self.api_key = api_key
        self.auth_mode = auth_mode
        self.model = model or self.DEFAULT_MODEL

    def is_configured(self) -> bool:
        return bool(self.api_key) or self.auth_mode == "login"

    def can_analyze(self) -> bool:
        return bool(self.api_key)

    def chat(self, system_prompt: str, messages: list, stream: bool = False) -> str:
        if self.auth_mode == "login" and not self.api_key:
            return self._chat_via_cli(system_prompt, messages)

        try:
            import anthropic
        except ImportError:
            raise ImportError("Instalá anthropic: pip install anthropic")

        client = anthropic.Anthropic(api_key=self.api_key)
        if stream:
            with client.messages.stream(
                model=self.model, max_tokens=8096,
                system=system_prompt, messages=messages
            ) as s:
                full = ""
                for text in s.text_stream:
                    print(text, end="", flush=True)
                    full += text
                print()
                return full
        response = client.messages.create(
            model=self.model, max_tokens=8096,
            system=system_prompt, messages=messages
        )
        return response.content[0].text

    def _chat_via_cli(self, system_prompt: str, messages: list) -> str:
        import subprocess
        last_user_msg = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        full_prompt = (
            f"{system_prompt}\n\n"
            f"IMPORTANTE: No uses ninguna herramienta. Solo responde con texto.\n\n"
            f"{last_user_msg}"
        )
        try:
            result = subprocess.run(
                ["claude", "-p", full_prompt, "--output-format", "text",
                 "--dangerously-skip-permissions", "--allowedTools", ""],
                capture_output=True, text=True, timeout=180,
            )
            if result.returncode != 0:
                raise RuntimeError(f"claude CLI error: {result.stderr.strip()[:200]}")
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise RuntimeError("El CLI de Claude tardó demasiado. Usá una API key.")
        except FileNotFoundError:
            raise RuntimeError("No se encontró 'claude'. Instalá Claude Code.")

    def analyze_repo(self, prompt: str) -> str:
        return self.chat(
            system_prompt=(
                "Sos un arquitecto de software senior. Analizás repositorios y generás "
                "documentación de contexto estructurada en markdown. "
                "Respondés solo con el contenido del archivo, sin explicaciones adicionales."
            ),
            messages=[{"role": "user", "content": prompt}],
        )

    def analyze_diff(self, system_prompt: str, diff: str, task: str) -> str:
        prompt = (
            f"Analizá este git diff y task description.\n"
            f"Determiná qué cambió arquitecturalmente y proponé actualizaciones al contexto.\n\n"
            f"TASK: {task}\n\nGIT DIFF:\n{diff[:8000]}\n\n"
            f"Respondé con JSON: summary, impact_level, affected_files, "
            f"cross_repo_impact, context_updates, alert_content"
        )
        return self.chat(system_prompt=system_prompt, messages=[{"role": "user", "content": prompt}])


# ─── GEMINI ───────────────────────────────────────────────────────────────────

class GeminiProvider:
    name = "Gemini (Google)"
    max_context_chars = 400_000
    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: str, auth_mode: str = "none", model: str = ""):
        self.api_key = api_key
        self.auth_mode = auth_mode
        self.model = model or self.DEFAULT_MODEL

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def can_analyze(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        try:
            from google import genai
        except ImportError:
            raise ImportError("Instalá google-genai: pip install google-genai")
        if not self.api_key:
            raise RuntimeError("Se requiere una API key de Google.")
        return genai.Client(api_key=self.api_key)

    def chat(self, system_prompt: str, messages: list, stream: bool = False) -> str:
        from google.genai import types
        client = self._get_client()
        last_user_msg = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=65536,
        )
        print(f"  → {self.model} | {len(last_user_msg)} chars | recibiendo", end="", flush=True)
        full = ""
        for chunk in client.models.generate_content_stream(
            model=self.model, contents=last_user_msg, config=config,
        ):
            text = chunk.text or ""
            full += text
            print(".", end="", flush=True)
        print(f" {len(full)} chars OK")
        return full

    def analyze_repo(self, prompt: str) -> str:
        return self.chat(
            system_prompt=(
                "Sos un arquitecto de software senior. Analizás repositorios y generás "
                "documentación de contexto estructurada en markdown. "
                "Respondés solo con el contenido del archivo, sin explicaciones adicionales."
            ),
            messages=[{"role": "user", "content": prompt}],
        )

    def analyze_diff(self, system_prompt: str, diff: str, task: str) -> str:
        prompt = (
            f"Analizá este git diff y task description.\n"
            f"TASK: {task}\nGIT DIFF: {diff[:8000]}\n"
            f"Respondé con JSON: summary, impact_level, affected_files, "
            f"cross_repo_impact, context_updates, alert_content"
        )
        return self.chat(system_prompt=system_prompt, messages=[{"role": "user", "content": prompt}])
