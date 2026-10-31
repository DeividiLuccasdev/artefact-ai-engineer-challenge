"""Loopback-only visual demo; no production authentication or public deployment."""
import argparse
import json
import secrets
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from emporio.agent import Agent, Session
from emporio.data import StoreData
from emporio.policies import Policies
from emporio.provider import LlamaCpp


class DemoServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port, agent):
        super().__init__(("127.0.0.1", port), Handler)
        self.agent = agent
        self.sessions = {}
        self.guard = threading.Lock()
        self.origin = f"http://127.0.0.1:{port}"
        self.slots = threading.BoundedSemaphore(2)


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

    def do_GET(self):
        if not self.valid_host():
            return self.send(403, '{"error":"Invalid host"}')
        if self.path == "/":
            page = Path(__file__).with_name("chat.html").read_text(encoding="utf-8")
            return self.send(200, page, "text/html; charset=utf-8")
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
        try:
            cookies = SimpleCookie(self.headers.get("Cookie", ""))
            sid = cookies["emporio_session"].value if "emporio_session" in cookies else ""
            with self.server.guard:
                now = time.monotonic()
                self.server.sessions = {key: value for key, value in self.server.sessions.items()
                                        if now - value[1] < 3600}
                if sid not in self.server.sessions:
                    if len(self.server.sessions) >= 20:
                        return self.send(429, '{"error":"Session limit reached"}')
                    sid = secrets.token_urlsafe(32)
                    session = Session()  # No browser-controlled customer identity.
                else:
                    session = self.server.sessions[sid][0]
                self.server.sessions[sid] = (session, now)
            answer = self.server.agent.respond(session, text)
            self.send(200, json.dumps({"answer": answer}, ensure_ascii=False), cookie=sid)
        finally:
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
