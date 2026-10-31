import http.client
import json
import threading
import unittest

from emporio.web import DemoServer


class WebTests(unittest.TestCase):
    def setUp(self):
        class Echo:
            def respond(self, session, text):
                self_test.assertIsNone(session.customer_id)
                session._history.append({"content": text})
                return str(len(session._history)) + ":" + text
        self_test = self
        self.server = DemoServer(0, Echo())
        self.port = self.server.server_address[1]
        self.server.origin = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.cleanup_server)

    def cleanup_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def post(self, payload, cookie=None, origin=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        headers = {"Content-Type": "application/json", "Origin": origin or self.server.origin}
        if cookie:
            headers["Cookie"] = cookie
        connection.request("POST", "/chat", json.dumps(payload), headers)
        response = connection.getresponse()
        status, body, new_cookie = response.status, json.loads(response.read()), response.getheader("Set-Cookie")
        connection.close()
        return status, body, new_cookie

    def page(self, cookie=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request("GET", "/", headers={"Cookie": cookie} if cookie else {})
        response = connection.getresponse()
        response.read()
        self.assertEqual(response.status, 200)
        new_cookie = response.getheader("Set-Cookie")
        connection.close()
        return new_cookie

    def test_browser_sessions_are_isolated(self):
        cookie = self.page()
        status, body, changed = self.post({"message": "first"}, cookie)
        self.assertEqual((status, body["answer"]), (200, "1:first"))
        self.assertIn("HttpOnly", cookie)
        self.assertIsNone(changed)
        self.assertIsNone(self.page(cookie))
        self.assertEqual(self.post({"message": "second"}, cookie)[1]["answer"], "2:second")
        self.assertEqual(self.post({"message": "new"}, self.page())[1]["answer"], "1:new")

    def test_cross_origin_and_identity_override_are_rejected(self):
        self.assertEqual(self.post({"message": "hello"}, origin="https://other.example")[0], 403)
        self.assertEqual(self.post({"message": "hello", "customer_id": 10})[0], 400)

    def test_chat_does_not_create_a_session_in_a_delayed_response(self):
        status, _, cookie = self.post({"message": "hello"})
        self.assertEqual(status, 409)
        self.assertIsNone(cookie)

    def test_page_establishes_session_before_messages(self):
        self.assertIsNotNone(self.page())

    def test_expired_cookie_cannot_create_a_replacement_on_post(self):
        cookie = self.page()
        with self.server.guard:
            for entry in self.server.sessions.values():
                entry.last_seen -= 3601
        status, _, changed = self.post({"message": "hello"}, cookie)
        self.assertEqual(status, 409)
        self.assertIsNone(changed)

    def test_inflight_session_cannot_expire_during_parallel_request(self):
        from concurrent.futures import ThreadPoolExecutor
        started, release = threading.Event(), threading.Event()
        seen = []
        class BlockingAgent:
            def respond(self, session, text):
                seen.append(session)
                if text == "first":
                    started.set()
                    if not release.wait(timeout=3):
                        raise RuntimeError("test timeout")
                return text
        self.server.agent = BlockingAgent()
        cookie = self.page()
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.post, {"message": "first"}, cookie)
            self.assertTrue(started.wait(timeout=2))
            try:
                with self.server.guard:
                    for entry in self.server.sessions.values():
                        entry.last_seen -= 3601
                second = pool.submit(self.post, {"message": "second"}, cookie)
                status, _, changed = second.result(timeout=2)
                self.assertEqual(status, 200)
                self.assertIsNone(changed)
                self.assertIs(seen[0], seen[1])
            finally:
                release.set()
            self.assertEqual(first.result(timeout=2)[0], 200)
        with self.server.guard:
            self.assertEqual(next(iter(self.server.sessions.values())).active, 0)
