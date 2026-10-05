"""Resumable controller: first-problem check, then full cohort for each stage.

Started model requests are never resampled. The controller does not commit or
push. Completed runs are audited before it advances to the next stage.
"""
from __future__ import annotations

import fcntl
import argparse
from pathlib import Path
import subprocess
import sys
import threading
import time

from run_agent_harness import BASE, OUTPUTS, ROOT, read
from run_deterministic import write_json
from run_validity_repair import now


def runner_active(step):
    """Check an adopted runner without signalling it or accepting a reused PID."""
    path = Path('/proc') / str(step['pid'])
    try:
        command = [s.decode() for s in (path / 'cmdline').read_bytes().split(b'\0') if s]
    except FileNotFoundError:
        return False
    if not command:  # A reaped or zombie process has no command line.
        return False
    if command != step['command']:
        raise RuntimeError('Runner PID belongs to a different command; inspect before resume')
    return True


def wait_for_runner(step, output):
    """Observe an existing runner after a controller handoff; never regenerate."""
    while runner_active(step):
        time.sleep(2)
    result = read(output / 'run.json')
    if result['status'] not in ('finished', 'failed'):
        raise RuntimeError('Adopted runner stopped without terminal evidence')
    return 0 if result['status'] == 'finished' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=('context', 'models'), default='models')
    parser.add_argument('--workers', type=int, default=10)
    parser.add_argument('--adopt-running', action='store_true', help='Monitor an already-started runner during a controller handoff')
    options = parser.parse_args()
    if options.workers < 1:
        parser.error('--workers must be positive')
    folder = ROOT / 'results/harness'
    folder.mkdir(parents=True, exist_ok=True)
    stem = 'controller' if options.suite == 'context' else 'model_config_controller'
    with (folder / ('.' + stem + '.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = folder / (stem + '.json')
        record = read(path) if path.exists() else {'created_at': now(), 'steps': []}
        record.update(status='running', resumed_at=now(), workers_per_stage=options.workers)
        write_json(path, record)
        record_lock = threading.RLock()
        pilot = read(BASE / 'config.json')['names'][0]

        def save():
            with record_lock:
                write_json(path, record)

        def pilot_gate(mode):
            records = [r for p in (OUTPUTS[mode] / 'cells').glob('*/result.json') if (r := read(p))['name'] == pilot]
            config = read(OUTPUTS[mode] / 'config.json')
            if {tuple((r['model'], r['effort'])) for r in records} != {tuple(c) for c in config['conditions']}:
                raise RuntimeError('Pilot is missing a model condition')
            if any(r['agent_tool_checks'] == 0 for r in records):
                raise RuntimeError('Pilot completed without exercising the checker tool')
            if any(r['status'] != 'complete' for r in records):
                raise RuntimeError('Pilot has an incomplete result')
            if mode == 'model_config' and any(r['cost']['status'] != 'estimated' or r['deterministic_calls'] != 1
                                            or r['deterministic_tool_calls'] != 0 for r in records):
                raise RuntimeError('Pilot is missing usage or final cleanup evidence')

        def stage(mode, phase):
            label = mode + '_' + phase
            with record_lock:
                previous = [s for s in record['steps'] if s['label'] == label]
            last = previous[-1] if previous else None
            if last and last.get('returncode') == 0 and last.get('audit_returncode') == 0:
                if phase == 'pilot':
                    pilot_gate(mode)
                return
            adopting = last is not None and 'returncode' not in last
            if adopting and not options.adopt_running:
                raise RuntimeError('Interrupted controller step needs inspection before resume: ' + label)
            args = [sys.executable, 'src/run_agent_harness.py', '--mode', 'score_edges' if mode == 'model_config' else mode,
                    '--output', str(OUTPUTS[mode]), '--workers', str(options.workers)]
            if phase == 'pilot':
                args += ['--name', pilot]
            with (folder / (label + '.log')).open('a') as stream:
                if adopting:
                    step = last
                    if step['command'] != args:
                        raise RuntimeError('Adopted runner arguments changed')
                    with record_lock:
                        step['adopted_at'] = now()
                        save()
                    returncode = wait_for_runner(step, OUTPUTS[mode])
                else:
                    child = subprocess.Popen(args, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
                    step = {'label': label, 'command': args, 'pid': child.pid, 'started_at': now()}
                    with record_lock:
                        record['steps'].append(step)
                        save()
                    returncode = child.wait()
                with record_lock:
                    step.update(returncode=returncode, finished_at=now())
                    save()
                if returncode == 0:
                    checked = subprocess.run([sys.executable, 'src/audit_agent_harness.py', str(OUTPUTS[mode])],
                                             cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
                    with record_lock:
                        step['audit_returncode'] = checked.returncode
                        save()
            if step['returncode'] != 0 or step.get('audit_returncode') != 0:
                raise RuntimeError('Runner or evidence audit failed; stopped before next stage: ' + label)
            if phase == 'pilot':
                pilot_gate(mode)

        try:
            if options.suite == 'context':
                for mode in ('correctness', 'score'):
                    for phase in ('pilot', 'full'):
                        stage(mode, phase)
            else:
                for phase in ('pilot', 'full'):
                    stage('model_config', phase)
        except Exception as error:
            record.update(status='failed', error=str(error))
            save()
            raise
        record.update(status='finished', finished_at=now())
        save()


if __name__ == '__main__':
    main()
