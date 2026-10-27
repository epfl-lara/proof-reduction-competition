"""Hard whole-problem deadlines retain certificates and stop detached children."""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from proof_eval.evidence.io import fingerprint, read, write_json
from proof_eval.harness import budget, limits
from proof_eval.harness.audit import audit
from proof_eval.harness.config import RunConfig
from proof_eval.harness.configuration import load_inputs, prepare
from proof_eval.paths import ROOT
from proof_eval.providers.costs import CostConfig, estimate_token_cost
from proof_eval.providers.registry import DEFAULT_CONDITIONS, adapter
from proof_eval.verification.api import Evaluator

ACTOR = """
import json, subprocess, sys, time
from pathlib import Path
from proof_eval.evidence.io import now, read, write_json
from proof_eval.harness.configuration import starting_point
from proof_eval.harness.attempts import start_attempt, finish_attempt
from proof_eval.harness.prompts import budget_suffix, messages
from proof_eval.harness.session import ProofSession
from proof_eval.providers.events import parse_events
from proof_eval.providers.processes import enable_subreaper
from proof_eval.verification.api import Evaluator

enable_subreaper()
r=read(sys.argv[1]); stage=sys.argv[2]
folder=Path(sys.argv[1]).parent; pack=r['pack']; config=r['config']
evaluator=Evaluator(**r['evaluator'])
saved=read(folder/'test_candidate.json')
evaluator.evaluate=lambda *a, **k: saved['selected_evaluation']
budget=read(folder/'budget_started.json')
session=ProofSession(folder/'evidence',pack,evaluator,config['mode'],seed=starting_point(pack,config['mode']),deadline_at=budget['deadline_epoch'])
initial=messages(pack,seed=(session.seed_code,session.seed_evaluation))
remaining=budget['deadline_epoch']-time.time()
initial[1]['content']+=budget_suffix(config,budget,dict(total_usd=0.0),remaining,0)
write_json(folder/'input.json',dict(name=pack['name'],model=r['model'],effort=r['effort'],mode=config['mode'],messages=initial,seed_proof=session.seed_code,seed_evaluation=session.seed_evaluation))
attempt=folder/'attempt_00'; workspace=attempt/'workspace'; workspace.mkdir(parents=True)
write_json(attempt/'request.json',dict(provider=config['provider'],messages=initial,model=r['model'],reasoning_effort=r['effort'],mode=config['mode'],tool_instructions=config['tool_instructions'],cli=config['cli'],timeout=config['generation_timeout'],max_attempts=None,max_output_tokens=None,temperature=None))
write_json(attempt/'request_started.json',dict(started_at=now()))
start_attempt(attempt,session,initial,0,dict(status='not_started',total_usd=0.0,attempts=0),config['generation_timeout'],None,remaining)
session.check(saved['selected_proof'])
assert session.best_code==saved['selected_proof']
leaf_code='import ctypes, time; ctypes.CDLL(None).prctl(4, 0, 0, 0, 0); time.sleep(1000)' if stage=='generation_nondumpable' else 'import time; time.sleep(1000)'
leaf=subprocess.Popen([sys.executable,'-c',leaf_code,'_ProofEval_deadbeef.lean'],start_new_session=True)
model=subprocess.Popen([sys.executable,'-c','import time; time.sleep(1000)'],start_new_session=True)
write_json(folder/'test_children.json',dict(leaf=leaf.pid,model=model.pid))
write_json(attempt/'process.json',dict(pid=model.pid,started_at=now()))
if stage=='cleanup':
 usage=dict(input_tokens=20,cached_input_tokens=0,output_tokens=10)
 events=[dict(type='item.completed',item=dict(type='agent_message',text=saved['selected_proof'])),dict(type='turn.completed',usage=usage)]
 (attempt/'events.jsonl').write_text(''.join(json.dumps(e)+'\\n' for e in events))
 (workspace/'final.txt').write_text(saved['selected_proof'])
 generation=parse_events(events,saved['selected_proof'],0)
 write_json(attempt/'generation.json',generation)
 from proof_eval.harness.tracking import attempt_cost
 finish_attempt(attempt,session,generation,attempt_cost(config,r['model'],r['effort'],[generation]))
 write_json(folder/'before_final_cleanup.json',dict(proof=session.best_code,evaluation=session.best_evaluation))
 session.cleanup=lambda code: time.sleep(1000)
 session.deterministic(session.best_code,origin='final_harness')
else:
 (attempt/'events.jsonl').write_text('')
 time.sleep(1000)
"""


def _run_test_cell(output, config, pack, model, effort, evaluator, *, generator):
    """Exercise worker policy with an explicit supervisor-owned test deadline."""
    from proof_eval.harness.search import _run_cell

    folder = (
        output / "cells" / fingerprint((pack["name"], model, effort, config["mode"]))
    )
    folder.mkdir(parents=True, exist_ok=True)
    limits.start_budget(folder, config["problem_timeout_seconds"])
    return _run_cell(
        output, config, pack, model, effort, evaluator, generator=generator
    )


@pytest.fixture
def deadline_run(tmp_path, monkeypatch, provider):
    name = "CallElimCorrect.substOldPostSubset"
    model, effort = DEFAULT_CONDITIONS[provider][0]
    output = tmp_path / "run"
    packs = load_inputs()
    identity = {"path": sys.executable, "version": "test", "sha256": "test"}
    monkeypatch.setattr(adapter(provider), "cli_identity", lambda: identity)
    config = prepare(
        output,
        "score_edges",
        packs,
        conditions=[(model, effort)],
        restart_history=False,
        semantic_search=False,
        web_search=False,
        provider=provider,
        budget_tracking="time",
        problem_timeout_seconds=1.0,
        paths={
            "dataset_path": str(ROOT / "data/benchmark_data_warmup.jsonl"),
            "environments_path": str(ROOT / "environments.local.json"),
        },
    )
    evaluator = Evaluator(
        ROOT / "data/benchmark_data_warmup.jsonl",
        ROOT / "environments.local.json",
        tmp_path / "cache",
        timeout=60,  # Archived reference fingerprint.
        version_workers=2,
    )
    folder = output / "cells" / fingerprint((name, model, effort, "score_edges"))
    folder.mkdir(parents=True)
    saved = read(
        ROOT
        / "results/harness/06_refactor_regression/cells"
        / fingerprint((name, "gpt-6.1-sol", "max", "score_edges"))
        / "result.json"
    )
    write_json(folder / "test_candidate.json", saved)
    return output, config, packs[name], model, effort, evaluator, folder, saved


@pytest.mark.parametrize(
    "stage,provider",
    [
        ("generation", "codex"),
        ("cleanup", "codex"),
        ("generation", "lemex"),
        ("generation_nondumpable", "lemex"),
        ("generation", "claude"),
        ("generation", "agy"),
    ],
)
def test_hard_deadline_retains_best_and_kills_detached_tools(
    monkeypatch, stage, deadline_run
):
    output, config, pack, model, effort, evaluator, folder, saved = deadline_run
    popen = subprocess.Popen

    def spawn(argv, **kwargs):
        return popen([sys.executable, "-c", ACTOR, argv[-1], stage], **kwargs)

    monkeypatch.setattr(budget.subprocess, "Popen", spawn)
    started = time.monotonic()
    result = budget.run_cell(output, config, pack, model, effort, evaluator)
    assert read(folder / "cell_request.json")["evaluator"]["version_workers"] == 2
    assert time.monotonic() - started < 3.0
    assert result["status"] == "complete"
    assert result["selected_proof"] == saved["selected_proof"]
    assert result["selected_evaluation"] == saved["selected_evaluation"]
    assert result["time_budget"]["exhausted"] is True
    assert result["stop"]["kind"] == "time_limit"
    assert result["generation_status"] == (
        "received" if stage == "cleanup" else "budget_exhausted"
    )
    assert result["final_cleanup_status"] == (
        "interrupted_time_limit" if stage == "cleanup" else "skipped_time_limit"
    )
    for pid in read(folder / "test_children.json").values():
        proc = Path("/proc") / str(pid) / "stat"
        assert not proc.exists() or proc.read_text().rsplit(")", 1)[1].split()[0] == "Z"
    assert audit(output)["status"] == "passed"
    assert budget.run_cell(output, config, pack, model, effort, evaluator) == result
    write_json(
        folder / "budget_end.json", {"exhausted": False, "work_stopped_epoch": 0}
    )
    with pytest.raises(ValueError, match="supervised deadline"):
        audit(output)


@pytest.mark.parametrize("provider", ["lemex"])
@pytest.mark.parametrize(
    "ordering,failure",
    [
        ("supervisor_first", None),
        ("native_first", None),
        ("supervisor_first", "legacy_stop"),
        ("supervisor_first", "verification"),
        ("supervisor_first", "transport"),
        ("supervisor_first", "missing_exit"),
        ("supervisor_first", "short_timeout"),
        ("native_first", "early_timeout"),
    ],
)
def test_native_deadline_finalization_race(
    monkeypatch, deadline_run, ordering, failure
):
    """Force both wait() orderings using saved certificates and no subprocesses."""
    from proof_eval.harness.attempts import finish_attempt, record_stop, start_attempt
    from proof_eval.harness.configuration import starting_point
    from proof_eval.harness.outcomes import finalize_cell
    from proof_eval.harness.prompts import budget_suffix, messages
    from proof_eval.harness.session import ProofSession
    from proof_eval.harness.tracking import attempt_cost, stop_decision

    output, config, pack, model, effort, evaluator, folder, saved = deadline_run
    clock = [100.0]
    monkeypatch.setattr(time, "time", lambda: clock[0])
    monkeypatch.setattr(
        evaluator, "evaluate", lambda *a, **k: saved["selected_evaluation"]
    )
    worker_bytes = {}

    def worker_finalizes():
        started = read(folder / "budget_started.json")
        session = ProofSession(
            folder / "evidence",
            pack,
            evaluator,
            config["mode"],
            seed=starting_point(pack, config["mode"]),
            deadline_at=started["deadline_epoch"],
        )
        request = messages(pack, seed=(session.seed_code, session.seed_evaluation))
        before_cost = attempt_cost(config, model, effort, [], name=pack["name"])
        remaining = started["deadline_epoch"] - clock[0]
        request[1]["content"] += budget_suffix(
            config, started, before_cost, remaining, 0
        )
        write_json(
            folder / "input.json",
            dict(
                name=pack["name"],
                model=model,
                effort=effort,
                mode=config["mode"],
                messages=request,
                seed_proof=session.seed_code,
                seed_evaluation=session.seed_evaluation,
            ),
        )
        attempt = folder / "attempt_00"
        timeout = remaining / 2 if failure == "short_timeout" else remaining
        start_attempt(
            attempt, session, request, 0, before_cost, timeout, None, remaining
        )
        write_json(
            attempt / "request.json",
            dict(
                provider=config["provider"],
                messages=request,
                model=model,
                reasoning_effort=effort,
                mode=config["mode"],
                tool_instructions=config["tool_instructions"],
                cli=config["cli"],
                timeout=timeout,
                max_attempts=None,
                max_output_tokens=None,
                temperature=None,
            ),
        )
        session.check(saved["selected_proof"])
        clock[0] = started["deadline_epoch"] + (
            -0.1 if failure == "early_timeout" else 0.1
        )
        termination = dict(
            at=datetime.fromtimestamp(clock[0], timezone.utc).isoformat(),
            returncode=-9,
            controlled=failure != "transport",
            reason="unexpected_exit" if failure == "transport" else "deadline",
            monitor_error=None,
        )
        generation = adapter(config["provider"]).parse_events([], "", -9)
        generation.update(
            status="transport_error" if failure == "transport" else "budget_exhausted",
            error="Native agent reached the problem time limit; not resampled",
            provider=config["provider"],
            usage=None,
            returncode=-9,
            process_exit=termination,
        )
        write_json(attempt / "termination.json", termination)
        if failure == "missing_exit":
            (attempt / "termination.json").unlink()
        write_json(attempt / "generation.json", generation)
        (attempt / "events.jsonl").write_text("")
        cost = attempt_cost(config, model, effort, [generation], name=pack["name"])
        finish_attempt(attempt, session, generation, cost)
        stop = stop_decision(
            config,
            generation,
            cost,
            unavailable=failure == "verification",
            round_number=0,
            time_remaining=started["deadline_epoch"] - clock[0],
        )
        if failure == "legacy_stop":
            # Retain coverage of the exact pre-integration Qwen worker record.
            stop = {"kind": "infrastructure", "reason": generation["error"]}
        record_stop(folder, stop, 0)
        before = dict(proof=session.best_code, evaluation=session.best_evaluation)
        write_json(folder / "before_final_cleanup.json", before)
        finalize_cell(
            folder,
            config,
            pack,
            model,
            effort,
            session,
            [generation],
            before,
            time_budget=limits.time_budget_summary(folder, exhausted=False),
        )
        for relative in (
            "result.json",
            "search_stop.json",
            "attempt_00/attempt.json",
            "attempt_00/generation.json",
            "attempt_00/termination.json",
            "evidence/checks.jsonl",
        ):
            if (folder / relative).exists():
                worker_bytes[relative] = (folder / relative).read_bytes()
        # Deadline recovery must never request another verification.
        monkeypatch.setattr(
            evaluator, "evaluate", lambda *a, **k: pytest.fail("fresh Lean call")
        )

    class Worker:
        pid = 123456789
        returncode = 0
        waited = False

        def wait(self, timeout):
            if self.waited:
                return
            self.waited = True
            worker_finalizes()
            if ordering == "supervisor_first":
                raise subprocess.TimeoutExpired("worker", timeout)

    monkeypatch.setattr(budget.subprocess, "Popen", lambda *a, **k: Worker())
    stopped_pids = []

    def stop_worker(pid):
        stopped_pids.append(pid)
        return dict(terminated_pids=[], temporary_sources=[])

    monkeypatch.setattr(budget, "stop_tree", stop_worker)
    result = budget.run_cell(output, config, pack, model, effort, evaluator)
    assert stopped_pids == ([Worker.pid] if ordering == "supervisor_first" else [])
    assert result["status"] == (
        "complete" if failure in (None, "legacy_stop") else "incomplete"
    )
    assert result["selected_proof"] == saved["selected_proof"]
    assert result["selected_evaluation"] == saved["selected_evaluation"]
    assert result["generations"][0]["usage"] is None
    if failure == "missing_exit":
        assert not (folder / "attempt_00/termination.json").exists()
    if failure == "early_timeout":
        assert not (folder / "budget_end.json").exists()
        assert (folder / "result.json").read_bytes() == worker_bytes["result.json"]
    else:
        assert result["time_budget"]["exhausted"] is True
        assert result["stop"]["kind"] == "time_limit"
        assert (folder / "worker_result.json").read_bytes() == worker_bytes[
            "result.json"
        ]
        if failure != "short_timeout":
            assert audit(output)["status"] == "passed"
    for relative, contents in worker_bytes.items():
        if relative != "result.json":
            assert (folder / relative).read_bytes() == contents
    assert budget.run_cell(output, config, pack, model, effort, evaluator) == result


def test_resume_never_replenishes_problem_deadline(tmp_path, monkeypatch):
    monkeypatch.setattr(limits.time, "time", lambda: 100.0)
    original = limits.start_budget(tmp_path, 20)
    monkeypatch.setattr(limits.time, "time", lambda: 119.0)
    assert limits.start_budget(tmp_path, 20) == original
    assert (
        limits.time_budget_summary(tmp_path, exhausted=False)["elapsed_seconds"] == 19
    )
    with pytest.raises(ValueError, match="time limit changed"):
        limits.start_budget(tmp_path, 30)


def test_process_deadline_does_not_stop_an_unrelated_job():
    from proof_eval.providers.processes import stop_tree

    outsider = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(1000)"], start_new_session=True
    )
    owned = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(1000)"], start_new_session=True
    )
    try:
        stopped = stop_tree(owned.pid)
        owned.wait(timeout=2)
        assert outsider.poll() is None
        assert (
            owned.pid in stopped["terminated_pids"]
            and outsider.pid not in stopped["terminated_pids"]
        )
    finally:
        if owned.poll() is None:
            owned.kill()
            owned.wait()
        outsider.terminate()
        outsider.wait(timeout=2)


def test_qwen_native_configuration_and_unknown_price():
    config = RunConfig(
        provider="lemex", conditions=(("Qwen/Qwen3.8-Flash-Next", "xhigh"),)
    )
    assert config.problem_timeout_seconds == 28800
    cost = estimate_token_cost(
        CostConfig(*config.conditions[0]),
        {
            "input_tokens": 10,
            "output_tokens": 20,
            "cached_input_tokens": 0,
            "cache_write_input_tokens": 0,
            "reasoning_output_tokens": 0,
        },
    )
    assert cost["status"] == "unknown_price" and cost["total_usd"] is None
    with pytest.raises(ValueError, match="Unsupported model/effort"):
        RunConfig(provider="lemex", conditions=(("Qwen/Qwen3.8-Flash-Next", "high"),))


def test_agy_native_configuration_and_api_equivalent_cost_budget():
    config = RunConfig(provider="agy")
    assert config.conditions == (("gemini-3.8-flash", "high"),)
    assert config.problem_timeout_seconds is None
    assert config.budget_tracking == "cost"
    cost = estimate_token_cost(
        CostConfig(*config.conditions[0]),
        {
            "input_tokens": 10,
            "output_tokens": 20,
            "cached_input_tokens": 0,
            "cache_write_input_tokens": 0,
            "reasoning_output_tokens": 0,
        },
    )
    assert cost["status"] == "estimated"
    assert cost["total_usd"] == pytest.approx((10 * 0.75 + 20 * 3.75) / 1e6)
    with pytest.raises(ValueError, match="Unsupported model/effort"):
        RunConfig(provider="agy", conditions=(("gemini-3.8-flash", "max"),))
    tracked = RunConfig(provider="agy", budget_tracking="cost")
    assert tracked.budget_usd_per_problem == 3.0


def test_adding_unpriced_qwen_keeps_legacy_deepseek_auditable():
    assert (
        audit(ROOT / "results/harness/07_native_agents/deepseek_flash")["status"]
        == "passed"
    )


def test_budget_tracking_cost_restarts_from_best_declaration(tmp_path, monkeypatch):
    import json

    from proof_eval.harness import search

    name = "CallElimCorrect.substOldPostSubset"
    model, effort = ("gpt-6.1-sol", "max")
    output = tmp_path / "run"
    packs = load_inputs()
    identity = {"path": sys.executable, "version": "test", "sha256": "test"}
    monkeypatch.setattr(adapter("codex"), "cli_identity", lambda: identity)
    config = prepare(
        output,
        "score_edges",
        packs,
        conditions=[(model, effort)],
        restart_history=False,
        semantic_search=False,
        web_search=False,
        provider="codex",
        budget_tracking="cost",
        budget_usd_per_problem=1.0,
        problem_timeout_seconds=3600.0,
        paths={
            "dataset_path": str(ROOT / "data/benchmark_data_warmup.jsonl"),
            "environments_path": str(ROOT / "environments.local.json"),
        },
    )
    evaluator = Evaluator(
        ROOT / "data/benchmark_data_warmup.jsonl",
        ROOT / "environments.local.json",
        ROOT / ".proof-eval",
        timeout=60,  # Fixed historical reference fixture, not the fresh-run default.
    )
    saved = read(
        ROOT
        / "results/harness/06_refactor_regression/cells"
        / fingerprint((name, "gpt-6.1-sol", "max", "score_edges"))
        / "result.json"
    )
    evaluator.evaluate = lambda *a, **k: saved["selected_evaluation"]
    monkeypatch.setattr(search, "DeterministicCleanup", lambda *a: lambda code: None)

    invocations = []

    def mock_generator(*, folder, messages, session, **kwargs):
        invocations.append(
            {"folder": folder, "messages": messages, "best": session.best_code}
        )
        if len(invocations) == 1:
            session.check(saved["selected_proof"])
        return {
            "status": "received",
            "content": session.best_code,
            "finish_reason": "stop",
            "codex_usage": {
                "input_tokens": 100000,
                "cached_input_tokens": 90000,
                "cache_write_input_tokens": 0,
                "output_tokens": 50000,
                "reasoning_output_tokens": 30000,
            },
        }

    monkeypatch.setattr(search, "generate", mock_generator)
    result = _run_test_cell(
        output,
        config,
        packs[name],
        model,
        effort,
        evaluator,
        generator=mock_generator,
    )

    assert len(invocations) == 2
    assert len(result["generations"]) == 2
    assert invocations[1]["best"] == saved["selected_proof"]
    json_str = (
        invocations[1]["messages"][1]["content"]
        .split("Optimize this declaration using the supplied tools.\n", 1)[1]
        .split("\nWhole-problem", 1)[0]
    )
    payload = json.loads(json_str)
    assert payload["incumbent_declaration"] == saved["selected_proof"]
    assert (
        "Whole-problem cost budget: $1 USD" in invocations[1]["messages"][1]["content"]
    )
    assert result["cost"]["total_usd"] >= 1.0
    assert result["cost"]["over_budget_at_assumed_rates"] is True
    assert result["selected_proof"] == saved["selected_proof"]


def test_budget_tracking_can_be_explicitly_disabled(tmp_path, monkeypatch):
    from proof_eval.harness import search

    name = "CallElimCorrect.substOldPostSubset"
    model, effort = ("gpt-6.1-sol", "max")
    output = tmp_path / "run"
    packs = load_inputs()
    identity = {"path": sys.executable, "version": "test", "sha256": "test"}
    monkeypatch.setattr(adapter("codex"), "cli_identity", lambda: identity)
    config = prepare(
        output,
        "score_edges",
        packs,
        conditions=[(model, effort)],
        restart_history=False,
        semantic_search=False,
        web_search=False,
        provider="codex",
        budget_tracking=None,
        budget_usd_per_problem=3.0,
        problem_timeout_seconds=3600.0,
        paths={
            "dataset_path": str(ROOT / "data/benchmark_data_warmup.jsonl"),
            "environments_path": str(ROOT / "environments.local.json"),
        },
    )
    evaluator = Evaluator(
        ROOT / "data/benchmark_data_warmup.jsonl",
        ROOT / "environments.local.json",
        ROOT / ".proof-eval",
        timeout=60,  # Fixed historical reference fixture, not the fresh-run default.
    )
    saved = read(
        ROOT
        / "results/harness/06_refactor_regression/cells"
        / fingerprint((name, "gpt-6.1-sol", "max", "score_edges"))
        / "result.json"
    )
    evaluator.evaluate = lambda *a, **k: saved["selected_evaluation"]
    monkeypatch.setattr(search, "DeterministicCleanup", lambda *a: lambda code: None)

    invocations = []

    def mock_generator(*, folder, messages, session, **kwargs):
        invocations.append(folder)
        return {
            "status": "received",
            "content": session.best_code,
            "finish_reason": "stop",
            "codex_usage": {
                "input_tokens": 10000,
                "cached_input_tokens": 5000,
                "cache_write_input_tokens": 0,
                "output_tokens": 1000,
                "reasoning_output_tokens": 500,
            },
        }

    result = _run_test_cell(
        output,
        config,
        packs[name],
        model,
        effort,
        evaluator,
        generator=mock_generator,
    )
    assert len(invocations) == 1
    assert len(result["generations"]) == 1


def test_budget_tracking_time_restarts_while_time_remains(tmp_path, monkeypatch):
    from proof_eval.harness import search

    name = "CallElimCorrect.substOldPostSubset"
    model, effort = ("gpt-6.1-sol", "max")
    output = tmp_path / "run"
    packs = load_inputs()
    identity = {"path": sys.executable, "version": "test", "sha256": "test"}
    monkeypatch.setattr(adapter("codex"), "cli_identity", lambda: identity)
    config = prepare(
        output,
        "score_edges",
        packs,
        conditions=[(model, effort)],
        restart_history=False,
        semantic_search=False,
        web_search=False,
        provider="codex",
        budget_tracking="time",
        problem_timeout_seconds=3600.0,
        paths={
            "dataset_path": str(ROOT / "data/benchmark_data_warmup.jsonl"),
            "environments_path": str(ROOT / "environments.local.json"),
        },
    )
    evaluator = Evaluator(
        ROOT / "data/benchmark_data_warmup.jsonl",
        ROOT / "environments.local.json",
        ROOT / ".proof-eval",
        timeout=60,  # Fixed historical reference fixture, not the fresh-run default.
    )
    saved = read(
        ROOT
        / "results/harness/06_refactor_regression/cells"
        / fingerprint((name, "gpt-6.1-sol", "max", "score_edges"))
        / "result.json"
    )
    evaluator.evaluate = lambda *a, **k: saved["selected_evaluation"]
    monkeypatch.setattr(search, "DeterministicCleanup", lambda *a: lambda code: None)

    invocations = []
    fake_time = [0.0]

    def mock_time():
        return fake_time[0]

    monkeypatch.setattr(search.time, "time", mock_time)

    def mock_generator(*, folder, messages, session, **kwargs):
        invocations.append(folder)
        if len(invocations) == 1:
            fake_time[0] = 100.0
        else:
            fake_time[0] = 3590.0
        return {
            "status": "received",
            "content": session.best_code,
            "finish_reason": "stop",
            "codex_usage": {
                "input_tokens": 1000,
                "cached_input_tokens": 500,
                "cache_write_input_tokens": 0,
                "output_tokens": 100,
                "reasoning_output_tokens": 50,
            },
        }

    result = _run_test_cell(
        output,
        config,
        packs[name],
        model,
        effort,
        evaluator,
        generator=mock_generator,
    )
    assert len(invocations) == 2
    assert len(result["generations"]) == 2


def test_budget_tracking_cli_and_validation(monkeypatch):
    from proof_eval.harness import cli

    with pytest.raises(
        ValueError, match="Cost budget tracking cannot track unpriced model"
    ):
        RunConfig(
            provider="lemex",
            conditions=(("Qwen/Qwen3.8-Flash-Next", "xhigh"),),
            budget_tracking="cost",
        )

    cfg = RunConfig(
        provider="codex",
        conditions=(("gpt-6.1-sol", "max"),),
        budget_tracking="cost",
        budget_usd_per_problem=2.5,
    )
    assert cfg.budget_tracking == "cost"
    assert cfg.budget_usd_per_problem == 2.5

    cfg_time = RunConfig(
        provider="lemex",
        conditions=(("Qwen/Qwen3.8-Flash-Next", "xhigh"),),
        budget_tracking="time",
    )
    assert cfg_time.budget_tracking == "time"

    captured = []
    monkeypatch.setattr(
        cli,
        "run_pipeline",
        lambda run_cfg: captured.append(run_cfg.model) or {"status": "complete"},
    )
    cli.main(["run", "--budget-tracking", "cost", "--budget-usd", "2.0"])
    assert captured[-1].budget_tracking == "cost"
    assert captured[-1].budget_usd_per_problem == 2.0

    cli.main(["run", "--track-cost"])
    assert captured[-1].budget_tracking == "cost"

    cli.main(["run", "--track-time", "--provider", "lemex"])
    assert captured[-1].budget_tracking == "time"
