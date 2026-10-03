"""Per-attempt Lean validity service, outside the model's write restrictions."""
from __future__ import annotations

import json
from pathlib import Path
import socketserver
import tempfile
import threading
import uuid

from proof_eval import Evaluator
from proof_eval.metrics import validate_candidate
from run_deterministic import write_json
from validity_feedback import build_validity_feedback

MAX_REQUEST = 1024 * 1024


def check_code(context, code, evaluator=None):
    """Match the frozen helper's feedback semantics; never prepare a reference."""
    root = Path(context['evaluator_root'])
    evaluator = evaluator or Evaluator(root / 'data/benchmark_data_warmup.jsonl',
                                      root / 'environments.local.json', root / '.proof-eval')
    row = evaluator.dataset.get(context['name'])
    try:
        original = validate_candidate(row, code)[0] == validate_candidate(row, row['src'])[0]
    except ValueError:
        original = False
    if original:
        references = evaluator.get_reference(context['name'])['versions']
        if any(r['status'] != 'prepared' for r in references.values()):
            raise RuntimeError('Prepared reference unavailable')
        evaluation = {'status': 'passed', 'per_version': {
            v: {'status': 'passed', 'passed': True, 'diagnostics': []} for v in references}}
    else:
        evaluation = evaluator.evaluate(context['name'], code, versions='all')
    return build_validity_feedback(evaluation, context['required_versions'])


class ValidityService:
    def __init__(self, workspace, context, check=check_code):
        self.workspace = Path(workspace).resolve()
        # The service binds to the host-supplied theorem; requests contain code only.
        self.context = json.loads(json.dumps(context))
        self.check = check
        self.temporary = tempfile.TemporaryDirectory(prefix='arena-validity-')
        self.socket_path = str(Path(self.temporary.name) / 'check.sock')
        owner = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                try:
                    line = self.rfile.readline(MAX_REQUEST + 1)
                    if len(line) > MAX_REQUEST or not line.endswith(b'\n'):
                        raise ValueError('Invalid or oversized validity request')
                    request = json.loads(line)
                    if set(request) != {'code'} or not isinstance(request['code'], str):
                        raise ValueError('Only a code string is accepted')
                    feedback = owner.check(owner.context, request['code'])
                    evidence = owner.workspace / 'validity_checks'
                    if evidence.is_symlink():
                        raise ValueError('Evidence directory must not be a symlink')
                    evidence.mkdir(exist_ok=True)
                    write_json(evidence / (uuid.uuid4().hex + '.json'),
                               {'code': request['code'], 'feedback': feedback})
                    response = {'feedback': feedback}
                except Exception as error:
                    response = {'error': f'{type(error).__name__}: {error}'}
                try:
                    self.wfile.write(json.dumps(response, ensure_ascii=False).encode() + b'\n')
                except BrokenPipeError:
                    pass

        self.server = socketserver.ThreadingUnixStreamServer(self.socket_path, Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()
        write_json(self.workspace / 'validity_service.json', {'socket': self.socket_path})

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temporary.cleanup()
