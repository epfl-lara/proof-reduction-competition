"""Codex agent transport for the versioned structural/score-feedback studies.

The frozen one-shot transport is left unchanged. The score mode has no imposed
total token, attempt or wall-time budget. A completed final ends the agent's
search; partial tool discoveries survive process/provider failures.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from codex_proposal import DISABLED, cli_identity, parse_events
from proof_agent_tools import ProofToolService
from run_codex_baselines_isolated import launch_command
from run_deterministic import write_json
from run_validity_repair import now

ROOT = Path(__file__).resolve().parent.parent
MODELS = {'gpt-6-astra': {'max', 'low'}, 'gpt-6-luna': {'max'}}
COMMON_TOOLS = """Use the supplied tools with `python tools.py ...` in your workspace:
  search 'literal symbol or mathematical property' [--version VERSION] [--limit 30]
  outline relative/source/File.lean [--version VERSION]
  read relative/source/File.lean [--start 1 --end 180] [--version VERSION]
  goals candidate.lean
  check candidate.lean
  status
Write a complete replacement declaration to candidate.lean before checking it.
context.json lists your theorem, source file and pinned projects. Source tools
also search the pinned project's Lean dependencies. You may use ordinary shell
source inspection within these paths. All source projects are read-only to tools;
the host checker supplies Lean validation. Other experiment files and evaluator
code are out of scope. Do not launch additional models, access the network for
proofs, run deterministic optimization programs, or modify the tool client.
Before final output, use `python tools.py finish --reason 'short factual reason'`.
The final message must be the complete selected Lean declaration, without prose.
The original seed is already validated and measured. Start checking when you
have a proposed change; checking the unchanged seed does not discover an improvement.
"""
MODE_TOOLS = {
    'correctness': """Experiment mode: one structural proposal with correctness-only debugging.
Use source inspection to choose a credible rewrite. Check it and repair compiler
errors until it passes every required version. Stop at that first valid proposal
and return it, even if you are unsure whether its score is better. Do not request
candidate performance measurements or start another optimization after a pass.
The host will evaluate the score after the proposal has finished.
""",
    'score': """Experiment mode: iterative optimization with real score feedback.
After EVERY proposed change, run `python tools.py check candidate.lean`. The
response contains (length reduction %, heartbeat reduction %, compatibility %),
their combined score, correctness feedback, and the best all-version-valid proof
so far. A failed primary check scores zero. Use the combined score, not just source
length. Invalid or regressive attempts never replace the saved best proof.
After a valid result, keep investigating concrete ways to improve it: structural
alternatives, stronger lemmas, smaller local helpers, focused tactics or explicit
proof terms. Repair failures and compare the scores of valid alternatives. You
have no fixed total attempt, token or wall-time budget. Continue while you have
promising changes; a single failed or worse attempt need not end the search.
Keep brief factual notes in your workspace on tried changes and measured outcomes
so you avoid repeating them. Stop when you judge further improvements unlikely,
or the remaining ideas do not justify more attempts. This is a local stopping
decision, not a claim of global optimality. Call status to recover the best proof,
then finish with a short stopping reason and return that exact declaration.
""",
}


def tool_instructions(mode):
    if mode in ('score_edges', 'score_each'):
        common = COMMON_TOOLS.replace('The original seed is already validated and measured.',
                                     'The supplied seed is already validated and measured.')
        placement = '''The harness selected the better all-version-valid original or deterministic
seed before your call and will apply the fixed deterministic portfolio to your
best checked proof after your call. Reference denominators remain the original.
'''
        if mode == 'score_edges':
            placement += 'Deterministic cleanup is performed only before and after model search; no in-loop deterministic tool is available.\n'
        else:
            placement += '''You additionally have `python tools.py deterministic candidate.lean`.
After each changed proposal passes all required versions, call this tool before
your next rewrite. It runs the fixed host-side deterministic portfolio and
returns before/after scores, the cleaned declaration, and the best proof so far.
This supplied tool is permitted; do not run optimizer scripts directly.
Use the measurements to choose the proof to continue from. Invalid or worse
cleanups never replace the saved best. Invalid proposals need correctness repair
before cleanup. Do not repeat the cleanup on identical code; results are cached.
'''
        return common + '\n' + MODE_TOOLS['score'] + '\n' + placement
    return COMMON_TOOLS + '\n' + MODE_TOOLS[mode]


def command(*, binary, workspace, system_file, last_message, model, effort, mode):
    if model not in MODELS or effort not in MODELS[model] or mode not in (*MODE_TOOLS, 'score_edges', 'score_each'):
        raise ValueError('Unsupported model, effort or experiment mode')
    settings = {
        'model_reasoning_effort': effort, 'model_reasoning_summary': 'none',
        'model_instructions_file': str(system_file), 'developer_instructions': tool_instructions(mode),
        'include_environment_context': False, 'include_permissions_instructions': False,
        'include_collaboration_mode_instructions': False, 'include_apps_instructions': False,
        'skills.include_instructions': False, 'skills.bundled.enabled': False,
        'project_doc_max_bytes': 0, 'web_search': 'disabled', 'agents.enabled': False,
        'tools.update_plan.enabled': False, 'approval_policy': 'never',
        'tools.experimental_request_user_input.enabled': False, 'check_for_update_on_startup': False,
    }
    result = [str(binary), 'exec', '--ignore-user-config', '--ignore-rules', '--strict-config',
              '--ephemeral', '--skip-git-repo-check', '--sandbox', 'danger-full-access',
              '--color', 'never', '--json', '-C', str(workspace), '-m', model, '-o', str(last_message)]
    for key, value in settings.items():
        result += ['-c', key + '=' + json.dumps(value)]
    for feature in DISABLED:
        result += ['--disable', feature]
    return result + ['-']


def generate(*, folder, messages, model, effort, mode, session, context, expected_cli):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    if [m['role'] for m in messages] != ['system', 'user']:
        raise ValueError('Expected system and user messages')
    identity = cli_identity()
    if identity != expected_cli:
        raise ValueError('Codex executable changed')
    # Retain the historical one-proposal timeout only in the correctness control.
    timeout = 1800 if mode == 'correctness' else None
    request = {'messages': messages, 'model': model, 'reasoning_effort': effort,
               'mode': mode, 'tool_instructions': tool_instructions(mode), 'cli': identity,
               'timeout': timeout, 'max_attempts': None, 'max_output_tokens': None,
               'temperature': None, 'tool_context': context, 'auth': 'existing_codex_login'}
    with (folder / '.generation.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = folder / 'request.json'
        if path.exists() and json.loads(path.read_text()) != request:
            raise ValueError('Saved agent request changed')
        write_json(path, request)
        if (folder / 'generation.json').exists():
            return json.loads((folder / 'generation.json').read_text())
        if (folder / 'request_started.json').exists():
            result = {'status': 'indeterminate', 'error': 'Started request without terminal output; not resampled', 'usage': None}
            write_json(folder / 'generation.json', result)
            return result
        workspace = folder / 'workspace'
        workspace.mkdir(exist_ok=True)
        write_json(workspace / 'context.json', context)
        (workspace / 'tools.py').write_text((ROOT / 'src/proof_agent_client.py').read_text())
        (workspace / 'candidate.lean').write_text(session.seed_code)
        (folder / 'system.txt').write_text(messages[0]['content'])
        (folder / 'prompt.txt').write_text(messages[1]['content'])
        base = command(binary=identity['path'], workspace=workspace, system_file=folder / 'system.txt',
                       last_message=workspace / 'final.txt', model=model, effort=effort, mode=mode)
        protected = list(context['source_projects'].values())
        # The model may write only its workspace/runtime. The host-owned ledger,
        # requests, system prompt and input evidence are outside this writable root.
        subprocess.run(launch_command([sys.executable, '-c', 'pass'], workspace, protected),
                       check=True, capture_output=True)
        args = launch_command(base, workspace, protected)
        write_json(folder / 'command.json', {'argv': args, 'policy': 'host_ledger_readonly_sources'})
        env = {k: v for k, v in os.environ.items() if not k.startswith('RCP_')}
        started = time.monotonic()
        with ProofToolService(session, workspace), (folder / 'events.jsonl').open('w') as out, (folder / 'stderr.log').open('w') as err:
            write_json(folder / 'request_started.json', {'started_at': now()})
            child = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=out, stderr=err,
                                     cwd=workspace, env=env, text=True, start_new_session=True)
            write_json(folder / 'process.json', {'pid': child.pid, 'started_at': now()})
            try:
                child.communicate(messages[1]['content'], timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                timed_out = True
        if timed_out:
            result = {'status': 'indeterminate', 'error': 'Correctness control timed out; not resampled', 'usage': None}
        else:
            try:
                events = [json.loads(line) for line in (folder / 'events.jsonl').read_text().splitlines() if line.strip()]
                final = (workspace / 'final.txt').read_text() if (workspace / 'final.txt').exists() else ''
                result = parse_events(events, final, child.returncode)
            except (OSError, ValueError) as error:
                result = {'status': 'transport_error', 'error': str(error), 'usage': None}
        result.update(elapsed_seconds=time.monotonic() - started, finished_at=now())
        write_json(folder / 'generation.json', result)
        return result
