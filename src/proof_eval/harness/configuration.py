"""Frozen experiment inputs, cached-reference guards, and active configurations."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from proof_eval.evidence.audit import _implementation
from proof_eval.evidence.io import digest, fingerprint, read, write_json
from proof_eval.optimization.cleanup import BUDGET, METHODS
from proof_eval.paths import PACKAGE, ROOT, SNAPSHOTS
from proof_eval.providers.costs import CostConfig, estimate_configuration, rate_card
from proof_eval.providers.registry import DEFAULT_CONDITIONS, adapter, validate
from proof_eval.providers.retries import REQUEST_MAX_RETRIES, STREAM_MAX_RETRIES
from proof_eval.verification.feedback import all_versions_passed
from proof_eval.verification.references import (
    check_references,
    original_evaluation,
    require_valid,
    required_versions,
)

from . import semantic, web
from .carryover import freeze_carryover, restore_deadlines
from .incumbents import freeze_incumbents, saved_incumbent
from .prompts import tool_instructions
from .tracking import (
    ATTEMPT_EVIDENCE_VERSION,
    CLEANUP_RESERVE_SECONDS,
    BudgetTracking,
    resolve_budgets,
    validate_budgets,
)

BASE = ROOT / "results/one_shot/01_context_ablation"
OUTPUTS = {
    "correctness": ROOT / "results/harness/01_structural_context",
    "score": ROOT / "results/harness/02_score_search",
    "score_edges": ROOT / "results/harness/03_deterministic_edges",
    "score_each": ROOT
    / "results/harness/04_deterministic_each",  # Historical evidence only.
    "model_config": ROOT / "results/harness/05_model_config",
}
CONDITIONS = {
    "correctness": [("gpt-6-astra", "low"), ("gpt-6-luna", "max")],
    "score": [("gpt-6-astra", "max"), ("gpt-6-astra", "low"), ("gpt-6-luna", "max")],
}
CONDITIONS.update(
    {mode: list(CONDITIONS["score"]) for mode in ("score_edges", "score_each")}
)
RUN_MODES = ("score_edges",)
DEFAULT_MODE = "score_edges"
DEFAULT_OUTPUT = ROOT / "results/harness/06_refactor_regression"
DETERMINISTIC_MODES = ("score_edges",)
CONDITIONS["model_config"] = [("gpt-6.1-sol", "max"), ("gpt-6-astra", "max")]
ACTIVE_CONDITIONS = [("gpt-6.1-sol", "max"), ("gpt-6-astra", "max")]

PROMPT_FILES = (
    "prompts/refactor_system.md",
    "prompts/strategy_bank.json",
)


def load_inputs(base=BASE):
    packs = [read(path) for path in sorted((base / "inputs").glob("*.json"))]
    names = read(base / "config.json")["names"]
    if (
        not packs
        or len(packs) != len(names)
        or len({p["name"] for p in packs}) != len(packs)
        or {p["name"] for p in packs} != set(names)
    ):
        raise ValueError("Prepared inputs must match the complete declared cohort")
    return {p["name"]: p for p in packs}


def historical(name, model, effort):
    if (model, effort) not in CONDITIONS["score"]:
        return None, None
    stage = (
        "10_astra_low"
        if (model, effort) == ("gpt-6-astra", "low")
        else "09_codex_tools_baselines"
    )
    path = (
        ROOT
        / "results/one_shot"
        / stage
        / "cells"
        / fingerprint((name, model, effort, "original"))
        / "result.json"
    )
    return (path, read(path)) if path.exists() else (None, None)


def structural_control(name, model, effort):
    if (model, effort) not in CONDITIONS["correctness"]:
        return None, None
    path = (
        OUTPUTS["correctness"]
        / "cells"
        / fingerprint((name, model, effort, "correctness"))
        / "result.json"
    )
    if not path.exists():
        return None, None
    control = read(path)
    if control["status"] != "complete":
        raise ValueError("Structural control is incomplete: " + name)
    return path, control


def score_control(name, model, effort):
    if (model, effort) not in CONDITIONS["score"]:
        return None, None
    path = (
        OUTPUTS["score"]
        / "cells"
        / fingerprint((name, model, effort, "score"))
        / "result.json"
    )
    if not path.exists():
        return None, None
    control = read(path)
    if control["status"] != "complete":
        raise ValueError("Score-only control is incomplete: " + name)
    return path, control


def starting_point(pack, mode):
    original = original_evaluation(pack)
    if mode in DETERMINISTIC_MODES:
        candidate = pack["incumbent"]
        if (
            all_versions_passed(candidate, required_versions(pack))
            and candidate["scores"]["combined_pct"]
            > original["scores"]["combined_pct"] + 0.05
        ):
            require_valid(candidate, pack["row"], pack["proof"])
            return pack["proof"], candidate
    return pack["row"]["src"], original


def preflight_costs(conditions, provider="codex", *, budget_usd: float = 3.0):
    """No model calls or Lean measurements; use complete saved stage-03 traces."""
    source = OUTPUTS["score_edges"]
    source_config = read(source / "config.json")
    paths = sorted((source / "cells").glob("*/result.json"))
    records = [read(p) for p in paths]
    scenarios = []
    for model, effort in conditions:
        for source_model, source_effort in source_config["conditions"]:
            group = [
                r
                for r in records
                if (r["model"], r["effort"]) == (source_model, source_effort)
            ]
            if (
                len(group) != len(source_config["names"])
                or {r["name"] for r in group} != set(source_config["names"])
                or any(r["status"] != "complete" for r in group)
            ):
                raise ValueError("Cost scenario needs a complete source cohort")
            scenarios.append(
                estimate_configuration(
                    CostConfig(model, effort), group, budget_usd=budget_usd
                )
            )
    return {
        "rate_card": rate_card(provider),
        "scenarios": scenarios,
        "source_result_sha256": {str(p.relative_to(ROOT)): digest(p) for p in paths},
        "budget_policy": f"Report the ${budget_usd:g} cap per problem; no stopping rule is imposed in this configuration comparison.",
        "pricing_assumptions": (
            "Standard Gemini API rates effective through 2026-12-31; API-equivalent, not verified Antigravity billing; cache storage excluded."
            if provider == "agy"
            else "Standard, short context per request, no regional premium; API-equivalent, not a Codex invoice."
        ),
    }


def prepare(
    output,
    mode,
    packs,
    conditions=None,
    *,
    base_directory=BASE,
    paths=None,
    provider="codex",
    problem_timeout_seconds: float | None = None,
    budget_tracking: BudgetTracking = "auto",
    budget_usd_per_problem: float = 3.0,
    max_budget_restarts: int = 20,
    max_transport_restarts: int = 2,
    incumbents_from: Path | None = None,
    carry_budgets_from: Path | None = None,
    semantic_search: semantic.SemanticSearchConfig | bool | None = True,
    web_search: bool = True,
) -> dict:
    if type(web_search) is not bool:
        raise ValueError("web_search must be a boolean")
    if mode not in RUN_MODES:
        raise ValueError("Unsupported or retired search mode: " + mode)
    conditions = conditions or DEFAULT_CONDITIONS[provider]
    budget_tracking, problem_timeout_seconds = resolve_budgets(
        budget_tracking, problem_timeout_seconds, conditions
    )
    validate_budgets(
        budget_tracking,
        budget_usd_per_problem,
        max_budget_restarts,
        problem_timeout_seconds,
        conditions,
    )
    if len({tuple(c) for c in conditions}) != len(conditions):
        raise ValueError("Duplicate model conditions")
    validate(provider, conditions)
    costs = preflight_costs(conditions, provider, budget_usd=budget_usd_per_problem)
    base_directory = base_directory.resolve()
    base = read(base_directory / "config.json")
    if len(packs) != len(base["names"]) or set(packs) != set(base["names"]):
        raise ValueError("Prepared inputs must match the complete declared cohort")
    semantic_search = semantic.resolve(semantic_search)
    pins = {str(p.relative_to(ROOT)): digest(p) for p in sorted(PACKAGE.rglob("*.py"))}
    pins.update({p: digest(ROOT / p) for p in PROMPT_FILES})
    for relative, expected in base["code_sha256"].items():
        _implementation(relative, expected, ROOT, SNAPSHOTS, "frozen input preparation")
    config = {
        "schema_version": 6,
        "attempt_evidence_version": ATTEMPT_EVIDENCE_VERSION,
        "provider": provider,
        "mode": mode,
        "names": base["names"],
        "conditions": [list(c) for c in conditions],
        "seed": (
            "best_original_or_saved_deterministic"
            if mode in DETERMINISTIC_MODES
            else "original"
        ),
        "code_sha256": pins,
        "input_sha256": {n: fingerprint(p) for n, p in packs.items()},
        "base_directory": str(base_directory),
        "base_config_sha256": digest(base_directory / "config.json"),
        "dataset_sha256": base["dataset_sha256"],
        "environment_config_sha256": base["environment_config_sha256"],
        "cli": adapter(provider).cli_identity(),
        "selection_margin_pp": 0.05,
        "deterministic_cleanup": mode in DETERMINISTIC_MODES,
        "candidate_feedback": mode,
        "max_total_attempts": (
            (max_budget_restarts if budget_tracking is not None else 0)
            + max_transport_restarts
            + 1
        ),
        "max_total_tokens": None,
        "generation_timeout": problem_timeout_seconds,
        "problem_timeout_seconds": problem_timeout_seconds,
        "time_budget_policy": (
            "one wall deadline per problem, including host tools and final cleanup; retain the best fully verified proof"
            if problem_timeout_seconds is not None
            else "no wall-time limit; cumulative cost budget only"
        ),
        "max_outer_correctness_repairs": 3 if mode == "correctness" else 0,
        "stop": (
            "first valid proposal"
            if mode == "correctness"
            else (
                "tracked budget, applicable wall-time cleanup reserve or restart safety limit; provider failures remain distinct"
                if budget_tracking is not None
                else "agent completion, explicit finish or problem deadline; provider failures remain distinct"
            )
        ),
        "historical_control_sha256": {},
        "structural_control_sha256": {},
        "tool_instructions": tool_instructions(
            mode,
            budget_tracking=budget_tracking,
            semantic_search=semantic_search is not None,
            web_search=web_search,
        ),
        "cost_estimate_sha256": fingerprint(costs),
        "cost_assumptions": {
            "service_tier": "standard",
            "context_band": "short",
            "regional_processing": False,
        },
        "budget_usd_per_problem": float(budget_usd_per_problem),
        "budget_tracking": budget_tracking,
        "budget_enforced": budget_tracking == "time",
        "cost_budget_policy": (
            "Host watches streamed usage at Gemini API-equivalent rates and stops the child at the remaining per-problem cap; cumulative attempt admission shares the same budget; an in-flight response may overshoot; unknown usage is never zero"
            if provider == "agy" and budget_tracking == "cost"
            else "native guard between upstream responses plus cumulative attempt admission; an in-flight response may overshoot; unknown usage is never zero"
        ),
        "cleanup_reserve_seconds": CLEANUP_RESERVE_SECONDS,
        "max_budget_restarts": int(max_budget_restarts),
        "max_transport_restarts": int(max_transport_restarts),
        "transport_recovery_version": 1,
        "native_retry_limits": (
            {
                "request_max_retries": REQUEST_MAX_RETRIES,
                "stream_max_retries": STREAM_MAX_RETRIES,
            }
            if provider == "lemex"
            else None
        ),
        "transport_recovery_policy": "Bounded backoff after observed terminal transient errors; reuse the best verified proof and the same selected problem budget; never resample indeterminate requests",
        "rate_card": rate_card(provider),
    }
    config.update(paths or {})
    if semantic_search is not None:
        config["semantic_search"] = semantic.freeze(semantic_search)
    if web_search:
        config["web_search"] = web.freeze()
    if type(max_transport_restarts) is not int or not 0 <= max_transport_restarts <= 20:
        raise ValueError("max_transport_restarts must be an integer between 0 and 20")
    config["incumbent_sources"] = freeze_incumbents(incumbents_from, config, packs)
    if carry_budgets_from is not None:
        if incumbents_from is not None:
            raise ValueError(
                "Budget carryover already reuses prior verified incumbents"
            )
        config["budget_carryover"] = freeze_carryover(carry_budgets_from, config, packs)
        config["incumbent_sources"].update(config["budget_carryover"])
    if config["incumbent_sources"]:
        config["seed"] = "best_original_deterministic_or_prior_same_condition"
    if mode in DETERMINISTIC_MODES:
        config.update(
            score_control_sha256={},
            deterministic_methods=list(METHODS),
            deterministic_budget=asdict(BUDGET),
            deterministic_jobs=str((output.parent / "deterministic_jobs").resolve()),
            deterministic_placement="beginning_and_end",
        )
    for name in config["names"]:
        for model, effort in conditions:
            path, _ = historical(name, model, effort)
            if path:
                config["historical_control_sha256"][str(path.relative_to(ROOT))] = (
                    digest(path)
                )
            if mode != "correctness":
                structural_path, _ = structural_control(name, model, effort)
                if structural_path:
                    config["structural_control_sha256"][
                        str(structural_path.relative_to(ROOT))
                    ] = digest(structural_path)
            if mode in DETERMINISTIC_MODES:
                score_path, _ = score_control(name, model, effort)
                if score_path:
                    config["score_control_sha256"][
                        str(score_path.relative_to(ROOT))
                    ] = digest(score_path)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "config.json"
    if path.exists() and read(path) != config:
        raise ValueError("Frozen experiment configuration changed")
    write_json(output / "cost_estimate.json", costs)
    write_json(path, config)
    restore_deadlines(output, config)
    return config


def guard(config, pack, evaluator):
    if config.get("web_search") is not None:
        web.guard(config["web_search"])
    if config.get("semantic_search") is not None:
        semantic.guard(config["semantic_search"])
    for relative, expected in config["code_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError("Frozen code changed: " + relative)
    for relative, field in [
        (
            config.get("dataset_path", "data/benchmark_data_warmup.jsonl"),
            "dataset_sha256",
        ),
        (
            config.get("environments_path", "environments.local.json"),
            "environment_config_sha256",
        ),
    ]:
        if digest(ROOT / relative) != config[field]:
            raise ValueError("Frozen input changed: " + relative)
    if (
        "references_sha256" in config
        and digest(config["references_path"]) != config["references_sha256"]
    ):
        raise ValueError("Frozen reference export changed")
    base_directory = Path(config.get("base_directory", BASE))
    if (
        digest(base_directory / "config.json") != config["base_config_sha256"]
        or fingerprint(pack) != config["input_sha256"][pack["name"]]
    ):
        raise ValueError("Frozen preparation changed")
    check_references(evaluator, pack, read(base_directory / "config.json"))
    for model, effort in config["conditions"]:
        saved_incumbent(config, pack, model, effort)
