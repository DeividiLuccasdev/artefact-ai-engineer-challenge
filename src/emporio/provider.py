"""Ollama native /api/chat adapter using the Python standard library."""
import json
import urllib.error
import urllib.request
from urllib.parse import urlparse

from emporio.agent import ProviderError


class Ollama:
    def __init__(self, model="qwen3:8b", base_url="http://localhost:11434", timeout=90):
        parsed = urlparse(base_url)
        # Keep original challenge data local; remote model endpoints are out of scope.
        if parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("Only local HTTP Ollama endpoints are supported")
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
            raise ValueError("Expected a local base URL without credentials or path")
        self.endpoint = base_url.rstrip("/") + "/api/chat"
        self.model, self.timeout = model, timeout

    def chat(self, messages, tools):
        request = urllib.request.Request(self.endpoint, data=json.dumps({
            "model": self.model, "messages": messages, "tools": tools, "stream": False,
            "think": False, "options": {"temperature": 0, "num_ctx": 16384}
        }).encode("utf-8"), headers={"Content-Type": "application/json"})
        try:
            # Disable environment proxy routing and redirects for local-only data flow.
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
            with opener.open(request, timeout=self.timeout) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ProviderError("Response exceeded size limit")
            body = json.loads(raw)
            message = body.get("message")
            if not isinstance(message, dict):
                raise ProviderError("Missing assistant message")
            return message
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, AttributeError) as exc:
            raise ProviderError("Ollama is unavailable or returned invalid JSON") from exc
