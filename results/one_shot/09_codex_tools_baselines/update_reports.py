"""Refresh the saved-evidence audit/report whenever another cell finishes."""
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def main():
    with (OUT / '.reporter.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous = None
        while True:
            current = sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in (OUT / 'cells').glob('*/result.json'))
            controller = json.loads((OUT / 'controller.json').read_text())
            if current != previous:
                result = subprocess.run([sys.executable, 'src/report_codex_baselines.py', '--input', str(OUT)], cwd=ROOT)
                with (OUT / 'report_history.jsonl').open('a') as history:
                    history.write(json.dumps({'at': datetime.now(timezone.utc).isoformat(), 'terminal_cells_observed': len(current), 'report_exit_code': result.returncode}) + '\n')
                if result.returncode:
                    return result.returncode
                previous = current
            if controller['status'] in {'finished', 'needs_inspection'}:
                return 0
            time.sleep(30)


if __name__ == '__main__':
    raise SystemExit(main())
