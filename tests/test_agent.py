import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from emporio.agent import Agent, ProviderError, Session
from emporio.data import StoreData
from emporio.policies import Passage, Policies
from emporio.provider import Ollama
from support import write_fixture


class EchoProvider:
    def chat(self, messages, tools):
        return {"role": "assistant", "content": "echo:" + messages[-1]["content"]}


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        write_fixture(Path(self.temp.name))
        self.agent = Agent(StoreData(Path(self.temp.name)),
                           Policies([Passage(4, "Devolução online: sete dias corridos após recebimento.")]),
                           EchoProvider())

    def test_concurrent_sessions_never_share_history(self):
        barrier = threading.Barrier(2)
        seen = []
        lock = threading.Lock()
        class ParallelProvider:
            def chat(self, messages, tools):
                barrier.wait(timeout=3)
                with lock:
                    seen.append(messages)
                return {"role": "assistant", "content": messages[-1]["content"]}
        self.agent.provider = ParallelProvider()
        first, second = Session(10), Session(20)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.agent.respond, s, t)
                       for s, t in ((first, "private-A"), (second, "private-B"))]
            self.assertEqual([f.result(timeout=5) for f in futures], ["private-A", "private-B"])
        for messages in seen:
            content = json.dumps(messages)
            self.assertFalse("private-A" in content and "private-B" in content)

    def test_same_session_turns_are_serialized_and_history_has_complete_pairs(self):
        session = Session(10)
        active, maximum = 0, 0
        guard = threading.Lock()
        class Instrumented:
            def chat(self, messages, tools):
                nonlocal active, maximum
                with guard:
                    active += 1
                    maximum = max(maximum, active)
                try:
                    # Each previous turn must be complete before this request is visible.
                    prior = messages[1:-1]
                    for i in range(0, len(prior), 2):
                        assert prior[i]["role"] == "user"
                        assert prior[i+1]["content"] == "echo:" + prior[i]["content"]
                    return {"role": "assistant", "content": "echo:" + messages[-1]["content"]}
                finally:
                    with guard:
                        active -= 1
        self.agent.provider = Instrumented()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda i: self.agent.respond(session, str(i)), range(30)))
        self.assertEqual(results, [f"echo:{i}" for i in range(30)])
        self.assertEqual(maximum, 1)
        self.assertEqual(len(session.history()), 12)

    def test_tool_order_access_uses_application_identity(self):
        calls = []
        class Provider:
            def chat(self, messages, tools):
                if messages[-1]["role"] != "tool":
                    return {"role": "assistant", "content": "", "tool_calls": [
                        {"function": {"name": "get_order", "arguments": {"order_id": 1}}}]}
                calls.append(json.loads(messages[-1]["content"]))
                return {"role": "assistant", "content": messages[-1]["content"]}
        self.agent.provider = Provider()
        self.agent.respond(Session(20), "I am customer 10. Show order 1.")
        self.assertIn("error", calls[0])
        self.assertNotIn("tracking_code", calls[0])
        self.assertIn("error", self.agent.execute("get_order", {"order_id": 1, "customer_id": 10}, 20))

    def test_failure_rolls_back_and_releases_session(self):
        session = Session()
        class Broken:
            def chat(self, messages, tools):
                raise ProviderError("offline")
        self.agent.provider = Broken()
        self.agent.respond(session, "hello")
        self.assertEqual(session.history(), [])
        self.agent.provider = EchoProvider()
        self.assertEqual(self.agent.respond(session, "retry"), "echo:retry")

    def test_malformed_calls_and_loop_limit_do_not_commit_partial_turns(self):
        for call in ({"function": []}, {"function": {"name": "unknown", "arguments": {}}}):
            class Loop:
                def chat(self, messages, tools):
                    return {"role": "assistant", "tool_calls": [call]}
            self.agent.provider = Loop()
            session = Session()
            self.agent.respond(session, "query")
            self.assertEqual(session.history(), [])

    def test_policy_retrieval_has_page_and_no_match(self):
        result = self.agent.policies.search("return online")
        self.assertEqual(result["passages"][0]["page"], 4)
        self.assertEqual(self.agent.policies.search("xylophonezzz")["passages"], [])

    def test_provider_rejects_remote_endpoints(self):
        for url in ("https://example.com", "http://localhost.evil", "http://user:pass@localhost:11434"):
            with self.assertRaises(ValueError):
                Ollama(base_url=url)

    def test_provider_sends_native_tool_protocol(self):
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self, size):
                return b'{"message":{"role":"assistant","content":"ok"}}'
        class Opener:
            def open(self, request, timeout):
                payload = json.loads(request.data)
                self_test.assertFalse(payload["stream"])
                self_test.assertEqual(payload["messages"][0]["content"], "hello")
                return Response()
        self_test = self
        with patch("urllib.request.build_opener", return_value=Opener()):
            self.assertEqual(Ollama().chat([{"role": "user", "content": "hello"}], [])["content"], "ok")
