"""Resume the frozen Codex cohort with shared Lean projects read-only to tools.

This additive execution adapter keeps the original generator's request and
no-resampling logic, scoring code and manifest. Each new attempt records the
extra launcher/service hashes. Historical requests are returned unchanged.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

import codex_proposal
from codex_validity_service import ValidityService
from run_deterministic import digest, write_json
import run_codex_baselines as frozen

ROOT = Path(__file__).resolve().parent.parent
EXECUTION_FILES = ('src/codex_readonly.py', 'src/codex_validity_client.py',
                   'src/codex_validity_service.py', 'src/run_codex_baselines_isolated.py')


def launch_command(command, folder, protected):
    folder = Path(folder).resolve()
    temporary = folder / 'runtime_tmp'
    temporary.mkdir(exist_ok=True)
    # Preserve the user's existing Codex authentication/runtime location.
    # Source projects are never among the writable roots.
    writable = [folder, Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))),
                Path.home() / '.cache', Path('/dev/null')]
    arguments = [sys.executable, str(ROOT / 'src/codex_readonly.py')]
    for path in writable:
        if path.exists():
            arguments += ['--writable', str(path.resolve())]
    for path in protected:
        arguments += ['--protected', str(Path(path).resolve())]
    return arguments + ['--temporary-directory', str(temporary), '--', *command]


@contextmanager
def protected_execution():
    original_command = codex_proposal.command
    original_cell = frozen.optimization_cell
    original_reference_check = frozen.check_references
    active = threading.local()
    pins = {path: digest(ROOT / path) for path in EXECUTION_FILES}

    def command(**kwargs):
        workspace = Path(kwargs['workspace'])
        folder = workspace.parent
        context = json.loads((workspace / 'context.json').read_text())
        protected = list(context['source_projects'].values())
        if not protected:
            raise ValueError('No source projects supplied')
        # Refuse unsupported kernels or overlapping writable roots before a
        # model request is sent. The same launcher protects the real process.
        preflight = launch_command([sys.executable, '-c', 'pass'], folder, protected)
        subprocess.run(preflight, check=True, capture_output=True, text=True)
        envelope = {'schema_version': 1, 'policy': 'readonly_sources_host_validity',
                    'code_sha256': pins, 'protected_projects': protected,
                    'request_sha256': digest(folder / 'request.json')}
        envelope_path = folder / 'execution_envelope.json'
        if envelope_path.exists() and json.loads(envelope_path.read_text()) != envelope:
            raise ValueError('Execution adapter identity changed')
        write_json(envelope_path, envelope)
        service = ValidityService(workspace, context)
        active.service = service
        service.start()
        (workspace / 'check_candidate.py').write_text((ROOT / 'src/codex_validity_client.py').read_text())
        return launch_command(original_command(**kwargs), folder, protected)

    def generate(**kwargs):
        active.service = None
        try:
            return codex_proposal.generate_once(**kwargs)
        finally:
            if active.service is not None:
                active.service.close()
                active.service = None

    def cell(**kwargs):
        kwargs.setdefault('generate', generate)
        return original_cell(**kwargs)

    def reference_check(evaluator, pack, config):
        try:
            return original_reference_check(evaluator, pack, config)
        except ValueError as error:
            current = evaluator.get_reference(pack['name'])['versions']
            details = {v: {'status': value.get('status'), 'diagnostics': value.get('diagnostics', [])}
                       for v, value in current.items() if value.get('status') != 'prepared'}
            raise ValueError(f'{error}; current reference diagnostics: {json.dumps(details)}') from error

    codex_proposal.command = command
    frozen.optimization_cell = cell
    frozen.check_references = reference_check
    try:
        yield
    finally:
        codex_proposal.command = original_command
        frozen.optimization_cell = original_cell
        frozen.check_references = original_reference_check


if __name__ == '__main__':
    with protected_execution():
        frozen.main()
