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

    def test_browser_sessions_are_isolated(self):
        status, body, cookie = self.post({"message": "first"})
        self.assertEqual((status, body["answer"]), (200, "1:first"))
        self.assertIn("HttpOnly", cookie)
        self.assertEqual(self.post({"message": "second"}, cookie)[1]["answer"], "2:second")
        self.assertEqual(self.post({"message": "new"})[1]["answer"], "1:new")

    def test_cross_origin_and_identity_override_are_rejected(self):
        self.assertEqual(self.post({"message": "hello"}, origin="https://other.example")[0], 403)
        self.assertEqual(self.post({"message": "hello", "customer_id": 10})[0], 400)
