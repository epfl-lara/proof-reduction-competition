import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from codex_readonly import abi_version
from codex_validity_service import ValidityService, check_code
from run_codex_baselines_isolated import launch_command


@pytest.fixture
def landlock():
    try:
        version = abi_version()
    except (OSError, RuntimeError) as exc:
        pytest.skip(str(exc))
    if version < 3:
        pytest.skip('Landlock ABI >= 3 required')


def test_tools_can_read_sources_but_cannot_write_truncate_remove_or_escape(tmp_path, landlock):
    project = tmp_path / 'source'
    workspace = tmp_path / 'attempt'
    project.mkdir()
    workspace.mkdir()
    (project / 'Original.lean').write_text('original')
    (workspace / 'source_link').symlink_to(project, target_is_directory=True)
    script = '''
from pathlib import Path
import os
source, work = Path(__import__('sys').argv[1]), Path(__import__('sys').argv[2])
assert (source / 'Original.lean').read_text() == 'original'
(work / 'candidate.lean').write_text('candidate')
for operation in [lambda: (source / 'candidate.lean').write_text('bad'),
                  lambda: (source / 'Original.lean').write_text('bad'),
                  lambda: os.truncate(source / 'Original.lean', 0),
                  lambda: (source / 'Original.lean').unlink(),
                  lambda: (work / 'source_link/candidate.lean').write_text('bad')]:
    try:
        operation()
    except PermissionError:
        pass
    else:
        raise AssertionError('Source write was allowed')
'''
    cmd = launch_command([sys.executable, '-c', script, str(project), str(workspace)], workspace, [project])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert (project / 'Original.lean').read_text() == 'original'
    assert not (project / 'candidate.lean').exists()
    assert (workspace / 'candidate.lean').read_text() == 'candidate'


def test_misconfigured_writable_ancestor_is_rejected(tmp_path, landlock):
    project = tmp_path / 'source'
    project.mkdir()
    cmd = launch_command([sys.executable, '-c', 'raise AssertionError("must not execute")'], tmp_path, [project])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert 'overlaps a protected source tree' in result.stderr


def test_restricted_client_uses_host_checker_without_project_writes(tmp_path, landlock):
    source = tmp_path / 'source'
    workspace = tmp_path / 'attempt'
    source.mkdir()
    workspace.mkdir()
    calls = []
    feedback = {'kind': 'lean_validity', 'status': 'passed', 'all_versions_passed': True}

    def check(context, code):
        calls.append((context, code))
        # The checker lives outside the restricted tool process and can create
        # the temporary Lean source needed by the unchanged backend.
        (source / '_ProofEval_test.lean').write_text(code)
        (source / '_ProofEval_test.lean').unlink()
        return feedback

    context = {'name': 'fixed_theorem'}
    service = ValidityService(workspace, context, check=check)
    service.start()
    code = 'theorem x : True := by trivial'
    (workspace / 'candidate.lean').write_text(code)
    client = Path(__file__).resolve().parents[1] / 'src/codex_validity_client.py'
    (workspace / 'check_candidate.py').write_text(client.read_text())
    try:
        cmd = launch_command([sys.executable, str(workspace / 'check_candidate.py'), 'candidate.lean'], workspace, [source])
        # A caller in a different cwd still resolves the candidate in its workspace.
        result = subprocess.run(cmd, cwd=source, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == feedback
        assert calls == [(context, code)]
        evidence = list((workspace / 'validity_checks').glob('*.json'))
        assert len(evidence) == 1
        assert json.loads(evidence[0].read_text()) == {'code': code, 'feedback': feedback}
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client_socket:
            client_socket.connect(service.socket_path)
            client_socket.sendall(b'{"code":"x","name":"another_theorem"}\n')
            assert 'error' in json.loads(client_socket.makefile('rb').readline())
        assert len(calls) == 1
    finally:
        service.close()


def test_original_identity_uses_cached_reference_without_measurement():
    row = {'name': 'x', 'statement': 'theorem x : True', 'src': 'theorem x : True := by trivial'}

    class Dataset:
        def get(self, name):
            assert name == 'x'
            return row

    class Evaluator:
        dataset = Dataset()

        def get_reference(self, name):
            return {'versions': {'v1': {'status': 'prepared'}}}

        def evaluate(self, *args, **kwargs):
            raise AssertionError('Reference must not be remeasured')

    response = check_code({'evaluator_root': '.', 'name': 'x', 'required_versions': ['v1']}, row['src'], Evaluator())
    assert response['all_versions_passed']
    assert not any(k in json.dumps(response) for k in ['heartbeats', 'combined_pct', 'token_count'])
