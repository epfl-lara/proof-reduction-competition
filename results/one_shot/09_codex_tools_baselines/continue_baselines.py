"""Run the authorized stages sequentially, with two Codex workers total."""
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from run_deterministic import write_json


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    with (OUT / '.controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pilot = [json.loads(p.read_text()) for p in (OUT / 'cells').glob('*/result.json')
                 if json.loads(p.read_text())['model'] == 'gpt-6-astra']
        if len(pilot) < 2 or not all(r['repair']['final_valid'] for r in pilot[:2]):
            raise RuntimeError('Astra pilot must finish and validate before scale-out')
        state_path = OUT / 'controller.json'
        state = json.loads(state_path.read_text()) if state_path.exists() else {'created_at': now(), 'steps': []}
        tasks = [('astra_full', ['--model', 'gpt-6-astra', '--effort', 'max']),
                 ('luna_first_pair_all_efforts', ['--model', 'gpt-6-luna', '--name', 'CallElimCorrect.substOldPostSubset'])]
        for label, tail in tasks:
            if any(s['label'] == label and s.get('returncode') == 0 for s in state['steps']):
                continue
            step = {'label': label, 'started_at': now(), 'command': [sys.executable, 'src/run_codex_baselines.py', *tail]}
            state['steps'].append(step)
            state['status'] = 'running'
            write_json(state_path, state)
            with (OUT / (label + '.log')).open('a') as log:
                child = subprocess.Popen(step['command'], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                step['pid'] = child.pid
                write_json(state_path, state)
                step['returncode'] = child.wait()
            step['finished_at'] = now()
            write_json(state_path, state)
            if step['returncode']:
                state['status'] = 'needs_inspection'
                write_json(state_path, state)
                return
        # Confirm each Luna setting delivers real outputs before expanding it.
        for effort in ('max', 'high', 'medium'):
            label = 'luna_full_' + effort
            if any(s['label'] == label and s.get('returncode') == 0 for s in state['steps']):
                continue
            initial = [json.loads(p.read_text()) for p in (OUT / 'cells').glob('*/input.json')]
            selected = [p.parent / 'initial/generation.json' for p in (OUT / 'cells').glob('*/input.json')
                        if (v := json.loads(p.read_text()))['model'] == 'gpt-6-luna' and v['effort'] == effort
                        and v['name'] == 'CallElimCorrect.substOldPostSubset']
            if len(selected) != 2 or not all(p.exists() and json.loads(p.read_text()).get('status') == 'received' for p in selected):
                state['steps'].append({'label': label, 'status': 'not_expanded', 'reason': 'Pilot transport did not deliver two responses'})
                write_json(state_path, state)
                continue
            cmd = [sys.executable, 'src/run_codex_baselines.py', '--model', 'gpt-6-luna', '--effort', effort]
            step = {'label': label, 'command': cmd, 'started_at': now()}
            state['steps'].append(step)
            with (OUT / (label + '.log')).open('a') as log:
                child = subprocess.Popen(cmd, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                step['pid'] = child.pid
                write_json(state_path, state)
                step['returncode'] = child.wait()
            step['finished_at'] = now()
            write_json(state_path, state)
            if step['returncode']:
                state['status'] = 'needs_inspection'
                write_json(state_path, state)
                return
        state.update(status='finished', finished_at=now())
        write_json(state_path, state)


if __name__ == '__main__':
    main()
