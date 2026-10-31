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


class LlamaCpp(Ollama):
    """Local llama.cpp chat-completions adapter, preserving tool-call identifiers."""

    def __init__(self, model="qwen3:1.7b", base_url="http://127.0.0.1:11435", timeout=180):
        super().__init__(model, base_url, timeout)
        self.endpoint = base_url.rstrip("/") + "/v1/chat/completions"

    def chat(self, messages, tools):
        wire = []
        pending_ids = []
        for item in messages:
            message = dict(item)
            if message.get("tool_calls"):
                calls = []
                pending_ids = []
                for i, original in enumerate(message["tool_calls"]):
                    call = dict(original)
                    function = dict(call["function"])
                    if not isinstance(function["arguments"], str):
                        function["arguments"] = json.dumps(function["arguments"])
                    identifier = call.get("id", f"call_{len(wire)}_{i}")
                    calls.append({"id": identifier, "type": "function", "function": function})
                    pending_ids.append(identifier)
                message["tool_calls"] = calls
            elif message["role"] == "tool":
                if not pending_ids:
                    raise ProviderError("Orphaned tool response")
                message = {"role": "tool", "tool_call_id": pending_ids.pop(0),
                           "content": message["content"]}
            wire.append(message)
        request = urllib.request.Request(self.endpoint, data=json.dumps({
            "model": self.model, "messages": wire, "tools": tools,
            "stream": False, "temperature": 0, "max_tokens": 700,
            "chat_template_kwargs": {"enable_thinking": False}
        }).encode("utf-8"), headers={"Content-Type": "application/json"})
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
            with opener.open(request, timeout=self.timeout) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ProviderError("Response exceeded size limit")
            body = json.loads(raw)
            if body["choices"][0].get("finish_reason") == "length":
                raise ProviderError("Truncated model response")
            message = body["choices"][0]["message"]
            for call in message.get("tool_calls", []):
                arguments = call["function"]["arguments"]
                if isinstance(arguments, str):
                    call["function"]["arguments"] = json.loads(arguments)
            return message
        except (urllib.error.URLError, TimeoutError, OSError, ValueError,
                AttributeError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Local model is unavailable or returned an invalid response") from exc
