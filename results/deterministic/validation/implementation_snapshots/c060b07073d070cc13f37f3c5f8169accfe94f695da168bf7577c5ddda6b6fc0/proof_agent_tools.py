"""Host-owned proof ledger and scoped source tools for staged agent experiments.

Only the host evaluates proofs and writes evidence. The model receives either
correctness alone or the real competition score tuple. Original references are
read from their existing cache and are never measured by this module.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import fcntl
import hashlib
import json
from pathlib import Path
import re
import socketserver
import subprocess
import tempfile
import threading
import time

from proof_eval.metrics import validate_candidate
from proof_eval.model_context import build_context
from proof_eval.one_shot import FIELDS, context_for_prompt, fingerprint
from run_codex_baselines import original_evaluation
from run_combined_matrix import BUDGET, METHODS, cleanup_proof, require_valid
from run_deterministic import digest, write_json
from run_validity_repair import now, required_versions
from validity_feedback import all_versions_passed, build_validity_feedback


def code_identity(row, code):
    try:
        code = validate_candidate(row, code)[0]
    except ValueError:
        pass
    return hashlib.sha256(code.encode()).hexdigest()


class DeterministicCleanup:
    """Proof-keyed, shared cleanup jobs using the existing ten-method portfolio."""

    def __init__(self, root, pack, evaluator, provenance, guard):
        self.root, self.pack, self.provenance, self.guard = Path(root), pack, provenance, guard
        original = original_evaluation(pack)
        original_identity = code_identity(pack['row'], pack['row']['src'])

        class ReferenceAwareEvaluator:
            def __getattr__(self, name):
                return getattr(evaluator, name)

            def evaluate(self, name, code, *, versions='all'):
                if name == pack['name'] and code_identity(pack['row'], code) == original_identity:
                    return deepcopy(original)
                return evaluator.evaluate(name, code, versions=versions)

        self.evaluator = ReferenceAwareEvaluator()

    def __call__(self, code):
        code = validate_candidate(self.pack['row'], code)[0]
        key = fingerprint({'name': self.pack['name'], 'proof': code, 'provenance': self.provenance,
                           'methods': METHODS, 'budget': asdict(BUDGET)})
        folder = self.root / key
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / '.dispatch.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            reused = (folder / 'result.json').exists()
            result = cleanup_proof(evaluator=self.evaluator, row=self.pack['row'], proof=code,
                                   folder=folder, provenance=self.provenance, guard=self.guard)
            return {**result, 'job_path': str(folder), 'reused': reused,
                    'job_result_sha256': digest(folder / 'result.json')}


class ProofSession:
    def __init__(self, folder, pack, evaluator, mode, guard=lambda: None, *, seed=None, cleanup=None):
        if mode not in ('correctness', 'score', 'score_edges', 'score_each'):
            raise ValueError('Unknown feedback mode')
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.pack, self.evaluator, self.mode, self.guard = pack, evaluator, mode, guard
        self.row = pack['row']
        self.versions = required_versions(pack)
        self.original = original_evaluation(pack)
        self.seed_code, self.seed_evaluation = seed or (self.row['src'], self.original)
        if seed is not None:
            require_valid(self.seed_evaluation, self.row, self.seed_code)
            if self.seed_evaluation['scores']['combined_pct'] < self.original['scores']['combined_pct']:
                raise ValueError('Seed may not regress the original')
        self.best_code = self.seed_code
        self.best_evaluation = deepcopy(self.seed_evaluation)
        self.cleanup = cleanup
        cleanup_log = self.folder / 'deterministic.jsonl'
        self.cleanup_calls = [json.loads(s) for s in cleanup_log.read_text().splitlines()] if cleanup_log.exists() else []
        self.first_valid_code = None
        self.checks = []
        self.cache = {}
        if seed is not None:
            self.cache[code_identity(self.row, self.seed_code)] = self.seed_evaluation
        self.finished = None
        self.lock = threading.RLock()
        ledger = self.folder / 'checks.jsonl'
        if ledger.exists():
            for line in ledger.read_text().splitlines():
                record = json.loads(line)
                self._restore(record)
        if (self.folder / 'finished.json').exists():
            self.finished = json.loads((self.folder / 'finished.json').read_text())
        self._save_state()

    def _restore(self, record):
        self.checks.append(record)
        self.cache[record['code_sha256']] = record['evaluation']
        if record['all_versions_passed'] and self.first_valid_code is None:
            self.first_valid_code = record['code']
        if record['accepted']:
            self.best_code, self.best_evaluation = record['code'], record['evaluation']

    def _save_state(self):
        write_json(self.folder / 'state.json', {
            'name': self.pack['name'], 'mode': self.mode, 'updated_at': now(),
            'checks': len(self.checks), 'valid_checks': sum(r['all_versions_passed'] for r in self.checks),
            'improvements': sum(r['accepted'] for r in self.checks),
            'best_proof': self.best_code, 'best_evaluation': self.best_evaluation,
            'finished': self.finished,
            'deterministic_calls': len(self.cleanup_calls)})

    def _score_view(self, evaluation):
        scores = evaluation['scores']
        checks = evaluation.get('per_version', {})
        passing = sum(checks.get(v, {}).get('passed') is True for v in self.versions)
        return {'score_tuple_order': list(FIELDS[:3]),
                'score_tuple': [scores.get(k) for k in FIELDS[:3]],
                'total_score': scores.get('combined_pct'),
                'scores': scores,
                'passing_rate_pct': 100 * passing / len(self.versions),
                'source_tokens': evaluation.get('candidate', {}).get('length'),
                'primary_heartbeats': checks.get(self.versions[0], {}).get('heartbeats'),
                'note': 'Local fixed-reference score. A primary failure gates competition components/total to zero; actual passing_rate_pct is reported separately.'}

    def check(self, code, *, origin='agent_tool'):
        with self.lock:
            identity = code_identity(self.row, code)
            if self.finished and origin == 'agent_tool':
                raise ValueError('Session already finished')
            if self.mode == 'correctness' and self.first_valid_code is not None:
                if identity != code_identity(self.row, self.first_valid_code):
                    return {'kind': 'proposal_already_valid', 'stop': True,
                            'message': 'The first valid proposal has been saved. Return that declaration; further optimization belongs to the score experiment.'}
            self.guard()
            started = time.monotonic()
            duplicate = identity in self.cache
            if identity == code_identity(self.row, self.row['src']):
                evaluation = deepcopy(self.original)
            elif duplicate:
                evaluation = deepcopy(self.cache[identity])
            else:
                evaluation = self.evaluator.evaluate(self.pack['name'], code, versions='all')
            self.guard()
            valid = all_versions_passed(evaluation, self.versions)
            numeric = evaluation.get('scores', {}).get('combined_pct')
            accepted = valid and numeric is not None and numeric > self.best_evaluation['scores']['combined_pct'] + .05
            feedback = build_validity_feedback(evaluation, self.versions)
            previous = self.best_evaluation['scores']['combined_pct']
            record = {'number': len(self.checks) + 1, 'at': now(), 'origin': origin,
                      'code': code, 'code_sha256': identity, 'evaluation': evaluation,
                      'feedback': feedback, 'duplicate': duplicate,
                      'all_versions_passed': valid, 'accepted': accepted,
                      'previous_best_score': previous, 'elapsed_seconds': time.monotonic() - started}
            with (self.folder / 'checks.jsonl').open('a') as stream:
                stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n')
                stream.flush()
            self._restore(record)
            self._save_state()
            if self.mode == 'correctness':
                return feedback
            return {'kind': 'lean_score_feedback', **self._score_view(evaluation),
                    'correctness': feedback, 'all_versions_passed': valid,
                    'accepted_as_best': accepted, 'duplicate': duplicate,
                    'delta_from_previous_best_pp': None if numeric is None else numeric - previous,
                    'best_scores': self.best_evaluation['scores'],
                    'best_proof': self.best_code}

    def status(self):
        if self.mode == 'correctness':
            return {'kind': 'lean_correctness_status', 'proposal_valid': self.first_valid_code is not None,
                    'message': 'Stop after the first valid proposal; no candidate scores are exposed.'}
        return {'kind': 'lean_optimization_status', 'attempts': len(self.checks),
                **self._score_view(self.best_evaluation), 'best_proof': self.best_code,
                'finished': self.finished}

    def deterministic(self, code, *, origin='agent_tool'):
        """Expose one fixed cleanup pass, preserving raw and cleaned evidence."""
        with self.lock:
            if origin == 'agent_tool' and (self.mode != 'score_each' or self.finished):
                raise ValueError('Deterministic tool is available only during score_each search')
            if self.cleanup is None:
                raise ValueError('No deterministic portfolio configured')
            self.guard()
            self.check(code, origin='deterministic_input')
            before = self.checks[-1]
            valid = before['all_versions_passed']
            job = self.cleanup(code) if valid else None
            after = None
            if job is not None:
                require_valid(job['evaluation'], self.row, job['proof'])
                identity = code_identity(self.row, job['proof'])
                self.cache[identity] = job['evaluation']
                after = self.check(job['proof'], origin='deterministic_' + origin)
            record = {'number': len(self.cleanup_calls) + 1, 'at': now(), 'origin': origin,
                      'input_code_sha256': before['code_sha256'], 'input_check': before['number'],
                      'output_check': self.checks[-1]['number'] if job else None,
                      'status': job['status'] if job else 'skipped_invalid',
                      'job_path': job.get('job_path') if job else None,
                      'job_result_sha256': job.get('job_result_sha256') if job else None,
                      'counters': job.get('counters', {}) if job else {},
                      'reused': job.get('reused', False) if job else False}
            with (self.folder / 'deterministic.jsonl').open('a') as stream:
                stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n')
            self.cleanup_calls.append(record)
            self.guard()
            self._save_state()
            return {'kind': 'deterministic_feedback', 'status': record['status'],
                    'before': self._score_view(before['evaluation']),
                    'after': self._score_view(job['evaluation']) if job else None,
                    'cleaned_proof': job['proof'] if job else None,
                    'gain_over_input_pp': None if job is None else job['evaluation']['scores']['combined_pct'] - before['evaluation']['scores']['combined_pct'],
                    'accepted_as_best': after['accepted_as_best'] if after else False,
                    'correctness': before['feedback'], 'reused': record['reused'],
                    'best_proof': self.best_code, 'best_scores': self.best_evaluation['scores']}

    def dispatch(self, request):
        op = request.get('op')
        if op == 'check' and set(request) == {'op', 'code'} and isinstance(request['code'], str):
            return self.check(request['code'])
        if op == 'deterministic' and set(request) == {'op', 'code'} and isinstance(request['code'], str):
            return self.deterministic(request['code'])
        if op == 'status' and set(request) == {'op'}:
            return self.status()
        if op == 'finish' and set(request) == {'op', 'reason'}:
            if not isinstance(request['reason'], str) or not request['reason'].strip():
                raise ValueError('Provide a short factual stopping reason')
            with self.lock:
                self.finished = {'at': now(), 'reason': request['reason'][:2000], 'kind': 'agent_decision'}
                write_json(self.folder / 'finished.json', self.finished)
                self._save_state()
                return self.status()
        if op == 'goals' and set(request) == {'op', 'code'} and isinstance(request['code'], str):
            self.guard()
            observed = build_context(self.evaluator, self.row, request['code'], measure_costs=False)
            self.guard()
            return {'kind': 'lean_goal_observations', **context_for_prompt(observed, costs=False)}
        if op in ('search', 'read', 'outline'):
            return self.source(request)
        raise ValueError('Unknown operation or invalid fields')

    def source(self, request):
        op = request['op']
        allowed = {'op', 'version', 'query', 'limit'} if op == 'search' else {'op', 'version', 'path'} | ({'start', 'end'} if op == 'read' else set())
        if not set(request) <= allowed:
            raise ValueError('Unsupported source fields')
        version = request.get('version') or self.versions[0]
        if version not in self.versions:
            raise ValueError('Version outside this theorem')
        project = self.evaluator.projects[(self.row['source'], version)].resolve()
        if op == 'search':
            query = request.get('query')
            if not isinstance(query, str) or not query or '\n' in query or len(query) > 300:
                raise ValueError('Use one nonempty literal source query')
            limit = request.get('limit', 30)
            if type(limit) is not int or not 1 <= limit <= 100:
                raise ValueError('Search limit must be in 1..100')
            result = subprocess.run(['rg', '--hidden', '--follow', '-n', '-F', '-g', '*.lean', '-g', '!.git/**',
                                     '-g', '!_ProofEval_*', '-g', '!_ProofOptimize_*', '--', query, '.'],
                                    cwd=project, text=True, capture_output=True, timeout=30)
            if result.returncode not in (0, 1):
                raise ValueError('Source search failed: ' + result.stderr[:500])
            matches = result.stdout.splitlines()
            return {'kind': 'source_search', 'version': version, 'query': query,
                    'matches': [s[:1500] for s in matches[:limit]], 'truncated': len(matches) > limit}
        path = (project / request['path']).resolve()
        packages = project / '.lake/packages'
        roots = [project] + ([p.resolve() for p in packages.iterdir() if p.is_dir()] if packages.is_dir() else [])
        if not any(path.is_relative_to(root) for root in roots) or path.suffix != '.lean' or path.name.startswith('_Proof'):
            raise ValueError('Only pinned Lean source files may be read')
        lines = path.read_text().splitlines()
        if op == 'outline':
            pattern = re.compile(r'^\s*(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*(?:theorem|lemma|def|abbrev|inductive|structure|class|instance)\b')
            matches = [{'line': i, 'text': s[:1000]} for i, s in enumerate(lines, 1) if pattern.match(s)]
            return {'kind': 'source_outline', 'path': request['path'], 'version': version,
                    'declarations': matches[:200], 'truncated': len(matches) > 200}
        start, end = request.get('start', 1), request.get('end', 180)
        if type(start) is not int or type(end) is not int or start < 1 or end < start or end - start >= 400:
            raise ValueError('Read 1..400 lines at a time')
        text = '\n'.join(f'{i}: {s}' for i, s in enumerate(lines, 1) if start <= i <= end)
        return {'kind': 'source_excerpt', 'path': request['path'], 'version': version,
                'text': text[:32000], 'truncated': len(text) > 32000}


class ProofToolService:
    def __init__(self, session, workspace):
        self.session, self.workspace = session, Path(workspace)
        self.temporary = tempfile.TemporaryDirectory(prefix='arena-agent-')
        self.socket_path = str(Path(self.temporary.name) / 'tools.sock')
        owner = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                try:
                    line = self.rfile.readline(1024 * 1024 + 1)
                    if len(line) > 1024 * 1024 or not line.endswith(b'\n'):
                        raise ValueError('Oversized or incomplete tool request')
                    response = owner.session.dispatch(json.loads(line))
                except Exception as error:
                    response = {'kind': 'tool_error', 'error': f'{type(error).__name__}: {error}'}
                try:
                    self.wfile.write(json.dumps(response, ensure_ascii=False, allow_nan=False).encode() + b'\n')
                except BrokenPipeError:
                    pass

        self.server = socketserver.ThreadingUnixStreamServer(self.socket_path, Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        write_json(self.workspace / 'tool_service.json', {'socket': self.socket_path})
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temporary.cleanup()
