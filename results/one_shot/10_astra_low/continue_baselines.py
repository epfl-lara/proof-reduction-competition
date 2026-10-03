"""Run the first Astra/low pair, then the full cohort, with live audited reports."""
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from run_deterministic import write_json
from run_validity_repair import now

PILOT = 'CallElimCorrect.substOldPostSubset'


def main():
    with (OUT / '.controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = OUT / 'controller.json'
        state = json.loads(path.read_text()) if path.exists() else {'created_at': now(), 'steps': []}
        state.update(status='running', resumed_at=now())
        write_json(path, state)
        for label, extra in [('first_pair', ['--name', PILOT]), ('full_cohort', [])]:
            if any(s['label'] == label and s.get('returncode') == 0 for s in state['steps']):
                continue
            if label == 'full_cohort':
                pilots = [json.loads(p.read_text()) for p in (OUT / 'cells').glob('*/result.json')]
                pilots = [r for r in pilots if r['name'] == PILOT]
                if len(pilots) != 2 or any(r['repair']['attempts'][0]['generation']['status'] != 'received' for r in pilots):
                    state.update(status='needs_inspection', reason='Pilot transport did not deliver two responses')
                    write_json(path, state)
                    return 1
            command = [sys.executable, 'src/run_astra_low.py', '--output', str(OUT), *extra]
            step = {'label': label, 'command': command, 'started_at': now()}
            state['steps'].append(step)
            with (OUT / (label + '.log')).open('a') as log:
                child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                step['pid'] = child.pid
                write_json(path, state)
                previous = None
                audit_failure = False
                while True:
                    current = sorted(str(p) for p in (OUT / 'cells').glob('*/result.json'))
                    if (OUT / 'config.json').exists() and current != previous:
                        with (OUT / 'reporter.log').open('a') as report_log:
                            audit = subprocess.run([sys.executable, 'src/run_astra_low.py', '--output', str(OUT), '--report-only'],
                                cwd=ROOT, stdout=report_log, stderr=subprocess.STDOUT)
                        with (OUT / 'report_history.jsonl').open('a') as history:
                            history.write(json.dumps({'at': now(), 'completed_cells': len(current), 'returncode': audit.returncode}) + '\n')
                        audit_failure |= audit.returncode != 0
                        previous = current
                    if child.poll() is not None:
                        break
                    time.sleep(20)
                # A child can finish while a report is running; always audit
                # the terminal snapshot before expanding or declaring success.
                with (OUT / 'reporter.log').open('a') as report_log:
                    audit = subprocess.run([sys.executable, 'src/run_astra_low.py', '--output', str(OUT), '--report-only'],
                        cwd=ROOT, stdout=report_log, stderr=subprocess.STDOUT)
                with (OUT / 'report_history.jsonl').open('a') as history:
                    history.write(json.dumps({'at': now(), 'completed_cells': len(list((OUT / 'cells').glob('*/result.json'))),
                        'returncode': audit.returncode, 'terminal_snapshot': True}) + '\n')
                audit_failure |= audit.returncode != 0
                step.update(returncode=child.returncode, finished_at=now(), audit_failed=audit_failure)
            write_json(path, state)
            if step['returncode'] or audit_failure:
                state['status'] = 'needs_inspection'
                write_json(path, state)
                return 1
        state.update(status='finished', finished_at=now())
        write_json(path, state)
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
