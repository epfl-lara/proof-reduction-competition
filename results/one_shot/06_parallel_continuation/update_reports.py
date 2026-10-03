"""Refresh saved RCP reports and audit the completed continuation; no model calls."""
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
REPAIR = OUT / '03_repaired_context_ablation'
COMBINED = OUT / '04_combined_deterministic'
sys.path.insert(0, str(ROOT / 'src'))
from run_deterministic import write_json


def now():
    return datetime.now(timezone.utc).isoformat()


def run(script, *args):
    command = [sys.executable, 'src/' + script, *map(str, args)]
    result = subprocess.run(command, cwd=ROOT)
    with (OUT / 'report_history.jsonl').open('a') as history:
        history.write(json.dumps({'at': now(), 'command': command,
                                  'exit_code': result.returncode}) + '\n')
    return result.returncode


def main():
    with (OUT / '.reporter.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous, failures = None, 0
        while True:
            current = tuple(len(list((p / 'cells').glob('*/result.json')))
                            for p in (REPAIR, COMBINED))
            statuses = tuple(json.loads((p / 'run.json').read_text())['status']
                             for p in (REPAIR, COMBINED))
            finished = statuses == ('complete', 'complete')
            if current != previous or finished:
                commands = [('report_repair_matrix.py', '--input', REPAIR),
                            ('report_combined_matrix.py', '--input', COMBINED)]
                if finished:
                    commands += [
                        ('audit_validity_repair.py', '--input', REPAIR, '--complete'),
                        ('audit_combined_matrix.py', '--input', COMBINED, '--complete'),
                        ('analyze_repair_budgets.py', '--input', REPAIR, '--complete'),
                        ('analyze_rejected_cleanup.py', '--input', COMBINED, '--complete',
                         '--copy-receipt', COMBINED / 'validation/cleanup_reuse.json'),
                        ('plot_model_experiments.py', '--input', OUT),
                    ]
                failed = next((command for command in commands if run(*command)), None)
                if failed:
                    failures += 1
                    write_json(OUT / 'reporter_status.json', {
                        'at': now(), 'status': 'needs_inspection' if finished or failures >= 3 else 'retrying_snapshot',
                        'failed_command': list(map(str, failed)), 'consecutive_failures': failures})
                    if finished or failures >= 3:
                        return 1
                else:
                    failures = 0
                    previous = current
                    write_json(OUT / 'reporter_status.json', {
                        'at': now(), 'status': 'finished' if finished else 'watching',
                        'recorded_cells': current, 'run_statuses': statuses})
                    if finished:
                        return 0
            if statuses[0] not in {'running', 'waiting_for_initial_results', 'complete'} or statuses[1] not in {'running', 'waiting_for_repair_results', 'complete'}:
                write_json(OUT / 'reporter_status.json', {
                    'at': now(), 'status': 'needs_inspection', 'run_statuses': statuses})
                return 1
            # Reports can briefly observe files from adjacent publish steps.
            # Preserve failed snapshots; only retry while workers are active.
            time.sleep(45)


if __name__ == '__main__':
    raise SystemExit(main())
