"""Local HTTP transport; shares exactly the same evaluator and cache as Python."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from urllib.parse import parse_qs, urlsplit

from .api import EvaluationNotReady


def make_server(evaluator, *, port=8765, workers=2):
    if workers < 1:
        raise ValueError("workers must be positive")
    slots = threading.BoundedSemaphore(workers)

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, body):
            data = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self.connection.settimeout(15)
            url = urlsplit(self.path)
            if url.path == "/health":
                return self.respond(200, {"status": "ok"})
            if url.path == "/environments":
                return self.respond(200, evaluator.environments())
            if url.path == "/reference":
                try:
                    query = parse_qs(url.query)
                    result = evaluator.get_reference(query["name"][0], versions=query.get("versions", ["all"])[0])
                    return self.respond(200, result)
                except (KeyError, ValueError) as exc:
                    return self.respond(400, {"error": str(exc)})
            self.respond(404, {"error": "Unknown endpoint"})

        def do_POST(self):
            self.connection.settimeout(15)
            if self.path not in ("/evaluate", "/reward"):
                return self.respond(404, {"error": "Unknown endpoint"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 2 * 1024 * 1024:
                    return self.respond(413, {"error": "Expected a JSON request of at most 2 MiB"})
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("Request must be a JSON object")
                allowed = {"name", "code", "input_kind", "versions"}
                if self.path == "/reward":
                    allowed |= {"metric", "invalid_reward"}
                if set(payload) - allowed:
                    raise ValueError(f"Unknown request fields: {sorted(set(payload) - allowed)}")
                if not isinstance(payload.get("name"), str) or not isinstance(payload.get("code"), str):
                    raise ValueError("name and code must be strings")
                if not slots.acquire(blocking=False):
                    return self.respond(429, {"error": "All evaluation workers are busy; retry later"})
                try:
                    if self.path == "/evaluate":
                        result = evaluator.evaluate(**payload)
                    else:
                        result = {"reward": evaluator.reward(**payload)}
                finally:
                    slots.release()
                self.respond(200, result)
            except EvaluationNotReady as exc:
                self.respond(409, {"error": str(exc), "type": "EvaluationNotReady"})
            except (ValueError, KeyError, TypeError) as exc:
                self.respond(400, {"error": str(exc)})
            except OSError as exc:
                self.respond(503, {"error": str(exc)})

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(evaluator, *, port=8765, workers=2):
    server = make_server(evaluator, port=port, workers=workers)
    print(f"Proof evaluator listening on http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
