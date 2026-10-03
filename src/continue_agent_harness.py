"""Resumable controller: first-problem check, then full cohort for each stage.

Started model requests are never resampled. The controller does not commit or
push. Completed runs are audited before it advances to the next stage.
"""
from __future__ import annotations

import fcntl
import json
from pathlib import Path
import subprocess
import sys

from run_agent_harness import BASE, OUTPUTS, ROOT, read
from run_deterministic import write_json
from run_validity_repair import now


def main():
    folder = ROOT / 'results/harness'
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / '.controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = folder / 'controller.json'
        record = read(path) if path.exists() else {'created_at': now(), 'steps': []}
        record.update(status='running', resumed_at=now())
        write_json(path, record)
        pilot = read(BASE / 'config.json')['names'][0]
        for mode in ('correctness', 'score'):
            for phase in ('pilot', 'full'):
                label = mode + '_' + phase
                previous = [s for s in record['steps'] if s['label'] == label]
                if previous and previous[-1].get('returncode') == 0 and previous[-1].get('audit_returncode') == 0:
                    continue
                if previous and 'returncode' not in previous[-1]:
                    raise RuntimeError('Interrupted controller step needs inspection before resume: ' + label)
                args = [sys.executable, 'src/run_agent_harness.py', '--mode', mode, '--workers', '5']
                if phase == 'pilot':
                    args += ['--name', pilot]
                with (folder / (label + '.log')).open('a') as stream:
                    child = subprocess.Popen(args, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
                    step = {'label': label, 'command': args, 'pid': child.pid, 'started_at': now()}
                    record['steps'].append(step)
                    write_json(path, record)
                    step['returncode'] = child.wait()
                    step['finished_at'] = now()
                    if step['returncode'] == 0:
                        checked = subprocess.run([sys.executable, 'src/audit_agent_harness.py', str(OUTPUTS[mode])],
                                                 cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
                        step['audit_returncode'] = checked.returncode
                if step['returncode'] != 0 or step.get('audit_returncode') != 0:
                    record['status'] = 'failed'
                    write_json(path, record)
                    raise RuntimeError('Runner or evidence audit failed; stopped before next stage: ' + label)
                if phase == 'pilot':
                    records = [read(p) for p in (OUTPUTS[mode] / 'cells').glob('*/result.json')]
                    if any(r['agent_tool_checks'] == 0 for r in records):
                        record.update(status='failed', error='Pilot completed without exercising the checker tool')
                        write_json(path, record)
                        raise RuntimeError(record['error'])
                write_json(path, record)
        record.update(status='finished', finished_at=now())
        write_json(path, record)


if __name__ == '__main__':
    main()
