"""Loopback-only visual demo; no production authentication or public deployment."""
import argparse
import json
import secrets
import socket
import threading
import time
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from dataclasses import dataclass

from emporio.agent import Agent, Session
from emporio.data import StoreData
from emporio.policies import Policies
from emporio.provider import LlamaCpp


@dataclass
class BrowserSession:
    session: Session
    last_seen: float
    active: int = 0


class DemoServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def server_bind(self):
        # Windows SO_REUSEADDR can let two independent demo processes bind one port.
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def __init__(self, port, agent):
        super().__init__(("127.0.0.1", port), Handler)
        self.agent = agent
        self.sessions = {}
        self.guard = threading.Lock()
        self.origin = f"http://127.0.0.1:{port}"
        self.slots = threading.BoundedSemaphore(2)

    def expire_idle(self, now):
        # Call under guard. Never evict a session while a turn is queued/running.
        self.sessions = {key: value for key, value in self.sessions.items()
                         if value.active or now - value.last_seen < 3600}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Do not persist messages or request bodies in HTTP access logs.
        pass

    def send(self, status, body, content_type="application/json; charset=utf-8", cookie=None):
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if cookie:
            self.send_header("Set-Cookie", f"emporio_session={cookie}; HttpOnly; SameSite=Strict; Path=/")
        self.end_headers()
        self.wfile.write(payload)

    def valid_host(self):
        return self.headers.get("Host") == self.server.origin.removeprefix("http://")

    def session_id(self):
        try:
            cookies = SimpleCookie(self.headers.get("Cookie", ""))
            return cookies["emporio_session"].value if "emporio_session" in cookies else ""
        except CookieError:
            return ""

    def do_GET(self):
        if not self.valid_host():
            return self.send(403, '{"error":"Invalid host"}')
        if self.path == "/":
            page = Path(__file__).with_name("chat.html").read_text(encoding="utf-8")
            sid = self.session_id()
            new_cookie = None
            full = False
            with self.server.guard:
                now = time.monotonic()
                self.server.expire_idle(now)
                if sid not in self.server.sessions:
                    if len(self.server.sessions) >= 20:
                        full = True
                    else:
                        sid = secrets.token_urlsafe(32)
                        self.server.sessions[sid] = BrowserSession(Session(), now)
                        new_cookie = sid
                else:
                    self.server.sessions[sid].last_seen = now
            if full:
                return self.send(429, '{"error":"Session limit reached"}')
            return self.send(200, page, "text/html; charset=utf-8", cookie=new_cookie)
        self.send(404, '{"error":"Not found"}')

    def do_POST(self):
        if (not self.valid_host() or self.headers.get("Origin") != self.server.origin
                or self.headers.get("Content-Type", "").split(";")[0] != "application/json"):
            return self.send(403, '{"error":"Invalid origin or content type"}')
        if self.path != "/chat":
            return self.send(404, '{"error":"Not found"}')
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 20000:
                raise ValueError("Invalid request size")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or set(payload) != {"message"}:
                raise ValueError("Expected message only")
            text = payload["message"]
            if not isinstance(text, str) or not 0 < len(text.strip()) <= 4000:
                raise ValueError("Message must contain 1-4000 characters")
        except (ValueError, TypeError):
            return self.send(400, '{"error":"Mensagem inválida."}')
        if not self.server.slots.acquire(blocking=False):
            return self.send(429, '{"error":"O assistente está ocupado. Tente novamente em instantes."}')
        entry = None
        try:
            sid = self.session_id()
            with self.server.guard:
                now = time.monotonic()
                self.server.expire_idle(now)
                entry = self.server.sessions.get(sid)
                if entry is not None:
                    entry.active += 1
                    entry.last_seen = now
            if entry is None:
                return self.send(409, '{"error":"Sua sessão expirou. Recarregue a página para iniciar outra conversa."}')
            answer = self.server.agent.respond(entry.session, text)
            # A slow response must never overwrite the browser's current identity.
            self.send(200, json.dumps({"answer": answer}, ensure_ascii=False))
        finally:
            if entry is not None:
                with self.server.guard:
                    entry.active -= 1
                    entry.last_seen = time.monotonic()
            self.server.slots.release()


def main():
    parser = argparse.ArgumentParser(description="Local-only Empório chat demo")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--policies", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    agent = Agent(StoreData(args.data_dir), Policies.from_pdf(args.policies), LlamaCpp())
    server = DemoServer(args.port, agent)
    print(f"Local chat: {server.origin}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
