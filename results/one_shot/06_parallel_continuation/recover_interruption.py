"""One-off audited recovery after the parent turn interrupted all workers."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from proof_eval.rcp import parse_env_file
from run_deterministic import write_json, digest


def read(path):
    return json.loads(path.read_text())


def main():
    now = datetime.now(timezone.utc).isoformat()
    here = Path(__file__).resolve().parent
    recovery = here / 'interruption_recovery'
    if recovery.exists():
        raise RuntimeError('Recovery is one-off; inspect the saved receipt instead')
    high = here.parent / '05_qwen38_extension'
    pids = [425517, 433780, 447369, 776310]
    if any((Path('/proc') / str(pid)).exists() for pid in pids):
        raise RuntimeError('An old process identity is still present')
    gate = ROOT / '.proof-eval/rcp-admission'
    locks = [(gate / f'slot_{i}.lock').open('a') for i in range(5)]
    for lock in locks:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    repair = here / '03_repaired_context_ablation'
    log_path = here / 'admission/3e74638ea17d42749d69a83c8ce401fc.jsonl'
    events = [json.loads(line) for line in log_path.read_text().splitlines()]
    admitted = {e['ticket'] for e in events if e['event'] == 'admitted'}
    released = {e['ticket'] for e in events if e['event'] == 'released'}
    unsent = [e for e in events if e['event'] == 'queued' and e['ticket'] not in admitted]
    if len(admitted) != 33 or admitted != released or len(unsent) != 4:
        raise RuntimeError('Unexpected admission tail; manual review required')
    markers = [p for p in repair.glob('cells/*/rounds/*/request_started.json') if not (p.parent / 'generation.json').exists()]
    if len(markers) != 4:
        raise RuntimeError('Unexpected missing responses')
    generations = list(repair.glob('cells/*/rounds/*/generation.json'))
    original = here.parent / '03_repaired_context_ablation'
    new = [p for p in generations if not (original / p.relative_to(repair)).exists()]
    if len(new) != 33 or any(not (p.parent / 'result.json').exists() for p in new):
        raise RuntimeError('Released requests do not match saved new generation/result count')
    recovery.mkdir()
    receipt = {'at': now, 'cause': 'Parent turn interruption; no worker survived. The earlier stop coordinator never finished.',
               'old_processes_absent': pids, 'all_five_local_locks_acquired': True,
               'prior_admission_sha256': digest(log_path), 'admitted_and_released': 33,
               'new_saved_responses': {str(p.relative_to(ROOT)): digest(p) for p in new},
               'reset_never_admitted': [], 'status': 'audited'}
    for p in markers:
        started = datetime.fromisoformat(read(p)['started_at'])
        matches = [e for e in unsent if 0 <= (datetime.fromisoformat(e['at']) - started).total_seconds() < .001]
        if len(matches) != 1:
            raise RuntimeError('Cannot match marker to exactly one never-admitted queue event')
        archive = recovery / 'never_sent_markers' / p.relative_to(repair)
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_bytes(p.read_bytes())
        receipt['reset_never_admitted'].append({'path': str(p.relative_to(ROOT)), 'sha256': digest(p), 'queued_event': matches[0]})
    write_json(recovery / 'receipt.json', receipt)
    # Archive first. These are the only four markers reset, all known unsent.
    for p in markers:
        p.unlink()
    for folder in (high / '01_context_ablation', high / '03_repaired_context_ablation', high / '04_combined_deterministic'):
        p = folder / 'run.json'
        archived = recovery / ('before_' + folder.name + '_high_run.json')
        archived.write_bytes(p.read_bytes())
        record = read(p)
        record.update(status='interrupted', interrupted_at=now, interruption_receipt=str(recovery / 'receipt.json'))
        write_json(p, record)
    high_log = high / 'admission/87ecae4bfd7c45f092826517137b425a.jsonl'
    ev = [json.loads(line) for line in high_log.read_text().splitlines()]
    done = {e['ticket'] for e in ev if e['event'] == 'released'}
    unknown = [e for e in ev if e['event'] == 'admitted' and e['ticket'] not in done]
    if len(unknown) != 2:
        raise RuntimeError('Unexpected high-effort unknown calls')
    stop = {'status': 'stopped', 'stopped_at': now, 'barrier_released_at': now,
            'initial_pid': 425517, 'repair_pid': 433780,
            'method': 'Verified process absence after external interruption, not successful coordinator drain',
            'previous_coordinator_receipt_sha256': digest(high / 'stop_high_reasoning.json'),
            'admission_sha256': digest(high_log), 'admitted_calls_without_saved_response': unknown,
            'response_usage_for_unknown_calls': None, 'resampling_permitted': False,
            'saved_initial_results': len(list((high / '01_context_ablation/cells').glob('*/result.json'))),
            'planned_initial_results': 75, 'all_five_local_locks_acquired': True}
    write_json(high / 'external_interruption_stop.json', stop)
    for lock in locks:
        lock.close()
    # New calls explicitly use the repository credentials. Historical worker
    # environments are unavailable; do not assert which key they used.
    env = {k: v for k, v in os.environ.items() if not k.startswith('RCP_')}
    env.update({k: v for k, v in parse_env_file(ROOT / '.env').items() if k.startswith('RCP_')})
    command = read(here / 'launch.json')['command']
    combined = [sys.executable, 'src/run_combined_matrix.py', '--input', str(repair),
                '--output', str(here / '04_combined_deterministic'), '--workers', '2', '--watch']
    launches = []
    for label, cmd in [('repair', command), ('combined', combined)]:
        with (recovery / (label + '.log')).open('w') as log:
            child = subprocess.Popen(cmd, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        launches.append({'label': label, 'pid': child.pid, 'command': cmd})
    receipt.update(status='restarted', restarted_at=datetime.now(timezone.utc).isoformat(), launches=launches,
                   rcp_credential_source='repository .env explicitly loaded; inherited RCP variables removed; no credentials saved')
    write_json(recovery / 'receipt.json', receipt)
    print(json.dumps({'recovered_unsent': 4, 'unknown_high_requests_not_repeated': 2, 'launches': launches}))


if __name__ == '__main__':
    main()
