"""Exercise the localhost JSON transport with the real evaluator contracts."""

import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from proof_eval.api import Evaluator
from proof_eval.http import make_server
from test_api import FakeBackend


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        row = {
            "name": "toy", "source": "toy-project",
            "statement": "theorem toy : True",
            "src": "theorem toy : True := by exact True.intro",
            "proof_length": 10,
            "version_info": [{"v1": "a" * 40}],
        }
        dataset = root / "data.jsonl"
        dataset.write_text(json.dumps(row) + "\n")
        config = root / "env.json"
        config.write_text(json.dumps({"projects": [
            {"source": "toy-project", "version": "v1", "path": "."}
        ]}))
        self.backend = FakeBackend()
        self.evaluator = Evaluator(dataset, config, root / "cache", backend=self.backend)
        self.server = make_server(self.evaluator, port=0, workers=1)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, path, payload=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            if payload is None:
                connection.request("GET", path)
            else:
                connection.request("POST", path, json.dumps(payload), {"Content-Type": "application/json"})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_evaluation_returns_components_without_implicit_reference_measurement(self):
        status, result = self.request("/evaluate", {"name": "toy", "code": "by trivial", "input_kind": "body"})
        self.assertEqual(status, 200)
        self.assertEqual(result["scores"]["length_reduction_pct"], 80)
        self.assertIsNone(result["scores"]["heartbeat_reduction_pct"])
        self.assertFalse(any(ref for _, ref, _ in self.backend.calls))

    def test_reward_missing_baseline_uses_explicit_conflict_status(self):
        status, result = self.request("/reward", {"name": "toy", "code": "by trivial", "input_kind": "body"})
        self.assertEqual(status, 409)
        self.assertEqual(result["type"], "EvaluationNotReady")

    def test_prepared_reward_and_invalid_code_are_distinguished(self):
        self.evaluator.prepare_reference("toy")
        status, result = self.request("/reward", {"name": "toy", "code": "by trivial", "input_kind": "body"})
        self.assertEqual((status, result), (200, {"reward": .85}))
        status, result = self.request("/reward", {"name": "toy", "code": "by sorry", "input_kind": "body"})
        self.assertEqual((status, result), (200, {"reward": 0.0}))

    def test_reference_and_health_reads_do_not_compile(self):
        self.assertEqual(self.request("/health"), (200, {"status": "ok"}))
        status, result = self.request("/reference?name=toy")
        self.assertEqual(status, 200)
        self.assertEqual(result["versions"]["v1"]["status"], "reference_not_prepared")
        self.assertFalse(self.backend.calls)

    def test_unknown_request_fields_and_mutating_reference_endpoint_reject(self):
        status, _ = self.request("/evaluate", {"name": "toy", "code": "by trivial", "refresh": True})
        self.assertEqual(status, 400)
        self.assertEqual(self.request("/prepare", {"name": "toy"})[0], 404)
        self.assertFalse(self.backend.calls)


if __name__ == "__main__":
    unittest.main()
