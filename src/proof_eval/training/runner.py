"""One-shot GPU entry point for the exact human-authorized training release."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from proof_eval.evidence.immutable import immutable, read, sha
from proof_eval.training.bootstrap import configure_imports
from proof_eval.training.command import training_command
from proof_eval.training.gates import (
    require_launch_authorization,
    require_preparation_policy,
)


def stage(plan: dict, value: str, **extra) -> None:
    record = {"stage": value, "at_epoch": time.time(), **extra}
    immutable(Path(plan["home"]) / "stages" / f"{time.time_ns()}-{value}.json", record)
    print(json.dumps(record, ensure_ascii=False), flush=True)


def verify_sources(plan: dict, release: Path) -> None:
    for relative, expected in read(release / "source-manifest.json").items():
        if sha(release / relative) != expected:
            raise RuntimeError("RL release source changed: " + relative)
    runtime = Path(plan["harness_home"])
    if sha(runtime / "validated-release.json") != plan["harness_release_sha256"]:
        raise RuntimeError("Sealed harness release changed")
    harness_release = read(runtime / "validated-release.json")
    if (
        sha(runtime / "validated-source-manifest.json")
        != harness_release["source_manifest_sha256"]
    ):
        raise RuntimeError("Sealed harness manifest changed")
    for relative, expected in read(runtime / "validated-source-manifest.json").items():
        if sha(runtime / "runtime" / relative) != expected:
            raise RuntimeError("Sealed harness source changed: " + relative)
        if (
            relative == "src/proof_eval/verification/backend.py"
            and sha(release / relative) != expected
        ):
            raise RuntimeError(
                "Frozen measurement backend differs from sealed harness: " + relative
            )
    for name, version in plan["package_versions"].items():
        if importlib.metadata.version(name) != version:
            raise RuntimeError(
                "Training dependency differs from the inspected image: " + name
            )
    swift = Path(importlib.metadata.distribution("ms-swift").locate_file("swift"))
    for relative, expected in plan["swift_source_sha256"].items():
        if sha(swift / relative) != expected:
            raise RuntimeError("Training API source changed: " + relative)


def verify_authorization(plan: dict, release: Path) -> None:
    path = release / "launch-authorization.json"
    if sha(path) != plan["launch_authorization_sha256"]:
        raise RuntimeError("Human launch authorization changed")
    require_launch_authorization(plan, read(path))


def configure_harness(plan: dict, release: Path) -> str:
    source = configure_imports(release)
    import proof_eval
    from proof_eval import Evaluator
    from proof_eval.training.prepare import original_pack
    from proof_eval.training.session import TrainingProofSession
    from proof_eval.verification.metrics import token_count, validate_candidate
    from proof_eval.verification.references import required_versions

    if (
        Path(proof_eval.__file__).resolve()
        != (source / "proof_eval/__init__.py").resolve()
    ):
        raise RuntimeError("Another Arena harness package shadowed the verified source")
    assert all(
        callable(v)
        for v in [
            Evaluator,
            original_pack,
            TrainingProofSession,
            token_count,
            validate_candidate,
            required_versions,
        ]
    )
    return str(proof_eval.__file__)


def test_environment(release: Path) -> dict[str, str]:
    environment = dict(os.environ)
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(p) for p in sorted((release / "test-wheels").glob("*.whl"))]
        + [str(release / "src"), os.environ.get("PYTHONPATH", "")]
    )
    return environment


def verify_attention_dependencies(plan: dict, release: Path) -> dict:
    """Construct the unused frozen vision tower on meta, without inference/weights."""
    if plan.get("attention_backend") != "fused" or plan.get("vit_attn_impl") != "sdpa":
        raise RuntimeError(
            "This image needs cuDNN fused text attention and SDPA vision"
        )
    import torch
    from transformers import AutoConfig
    from transformers.models.qwen3_5 import Qwen3_5VisionModel

    snapshot = (
        Path(plan["base_model_cache"])
        / "models--Qwen--Qwen3.8-Flash-Next/snapshots"
        / plan["model_revision"]
    )
    if sha(snapshot / "config.json") != plan["model_config_sha256"]:
        raise RuntimeError("The original cached model config changed")
    config = AutoConfig.from_pretrained(
        str(snapshot), trust_remote_code=True, local_files_only=True
    )
    config.vision_config._attn_implementation = plan["vit_attn_impl"]
    with torch.device("meta"):
        vision = Qwen3_5VisionModel._from_config(config.vision_config)
    if not all(parameter.is_meta for parameter in vision.parameters()):
        raise RuntimeError("Attention preflight unexpectedly allocated model weights")
    result = {
        "vision_attention": vision.config._attn_implementation,
        "text_attention_backend": plan["attention_backend"],
        "all_parameters_meta": True,
        "model_generation_calls": 0,
    }
    del vision
    return result


def mirror_trainer_exit(root: Path, home: Path, code: int, plan_path: Path) -> dict:
    log = root / "training.log"
    size = log.stat().st_size
    with log.open("rb") as stream:
        offset = max(0, size - 128 * 1024)
        stream.seek(offset)
        tail = stream.read()
    record = {
        "exit_code": code,
        "at_epoch": time.time(),
        "log_path": str(log),
        "log_bytes": size,
        "tail_offset": offset,
        "tail_sha256": hashlib.sha256(tail).hexdigest(),
        "tail_utf8": tail.decode(errors="replace"),
        "source_plan_sha256": sha(plan_path),
    }
    immutable(home / "trainer-exit.json", record)
    return record


def preflight_only(plan: dict, release: Path) -> dict:
    """Exercise actual wiring without GPU, policy inference or Lean preparation."""
    verify_sources(plan, release)
    verify_authorization(plan, release)
    harness = configure_harness(plan, release)
    attention = verify_attention_dependencies(plan, release)
    from proof_eval.training.tools import freeze_host_tools

    tools = freeze_host_tools(plan)
    # Exercise imports and hook registration against the actual image packages.
    # Importing this plugin performs no sampling or optimizer step.
    from proof_eval.training.swift_plugin import ArenaReward, ArenaScheduler

    assert callable(ArenaReward) and callable(ArenaScheduler)
    post_import_tools = None
    if plan.get("semantic_regression"):
        from proof_eval.training.tools import verify_search_after_training_patch

        post_import_tools = verify_search_after_training_patch(plan, release, tools)
    tested = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(release / "tests")],
        cwd=release,
        env=test_environment(release),
        capture_output=True,
        text=True,
        timeout=90,
    )
    return {
        "status": "passed" if tested.returncode == 0 else "failed",
        "returncode": tested.returncode,
        "stdout": tested.stdout,
        "stderr": tested.stderr,
        "sources_verified": True,
        "authorization_verified": True,
        "harness_imports_verified": harness,
        "attention_dependencies": attention,
        "training_plugin_imported": True,
        "post_training_import_semantic_regression": post_import_tools,
        "host_tools": tools,
        "policy_model_calls": 0,
        "embedding_model_calls": tools["embedding_model_calls"],
        "source_manifest_sha256": sha(release / "source-manifest.json"),
        "model_calls": 0,
        "optimizer_steps": 0,
    }


def run(plan_path: Path, release: Path) -> None:
    plan = read(plan_path)
    os.environ["LEAN_NUM_THREADS"] = str(plan.get("lean_threads", 1))
    verify_sources(plan, release)
    verify_authorization(plan, release)
    configure_harness(plan, release)
    root, home = Path(plan["root"]), Path(plan["home"])
    root.mkdir(parents=True, exist_ok=False)
    started = {
        "pid": os.getpid(),
        "start_ticks": Path("/proc/self/stat")
        .read_text()
        .rsplit(")", 1)[1]
        .split()[19],
        "at_epoch": time.time(),
        "plan_sha256": sha(release / "plan.json"),
        "dispatch_once": True,
    }
    immutable(root / "started.json", started)
    immutable(home / "started.json", started)
    hardware = subprocess.check_output(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total",
            "--format=csv,noheader,nounits",
        ],
        text=True,
        timeout=10,
    ).splitlines()
    if len(hardware) != 8 or not all(
        "H200" in x and float(x.rsplit(",", 1)[1]) > 130000 for x in hardware
    ):
        raise RuntimeError("This baseline requires the declared eight H200 GPUs")
    immutable(root / "hardware.json", hardware)
    # Reproducible compiler caches are private to this new node-local process.
    private_cache = Path("/tmp") / (plan["experiment_id"] + "-" + str(os.getpid()))
    private_cache.mkdir(mode=0o700, exist_ok=False)
    for variable, suffix in {
        "XDG_CACHE_HOME": "xdg",
        "HF_MODULES_CACHE": "hf-modules",
        "TRITON_CACHE_DIR": "triton",
        "VLLM_CACHE_ROOT": "vllm",
        "TORCHINDUCTOR_CACHE_DIR": "inductor",
        "TORCH_EXTENSIONS_DIR": "torch-extensions",
        "CUDA_CACHE_PATH": "cuda",
    }.items():
        path = private_cache / suffix
        path.mkdir(mode=0o700)
        os.environ[variable] = str(path)
    immutable(
        root / "private-compiler-cache.json",
        {"root": str(private_cache), "initially_empty": True},
    )
    if shutil.disk_usage(root).free < 512 * 1024**3:
        raise RuntimeError(
            "Scratch has less than 512 GiB free for base weights, rollouts and checkpoints"
        )
    stage(plan, "model_free_tests", hardware=hardware)
    with (root / "model-free-tests.log").open("x") as log:
        tested = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", str(release / "tests")],
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=release,
            timeout=90,
            env=test_environment(release),
        )
    immutable(
        root / "model-free-tests.json",
        {
            "returncode": tested.returncode,
            "log_sha256": sha(root / "model-free-tests.log"),
        },
    )
    if tested.returncode:
        raise RuntimeError("Pinned-image RL tests failed")
    stage(plan, "attention_dependency_preflight", model_calls=0)
    immutable(
        home / "attention-preflight.json", verify_attention_dependencies(plan, release)
    )

    from proof_eval.training.tools import freeze_host_tools

    stage(plan, "host_tool_preflight", policy_model_calls=0)
    tools = freeze_host_tools(plan)
    immutable(root / "host-tools.json", tools)
    immutable(home / "host-tools.json", tools)

    inputs = root / "inputs"
    inputs.mkdir()
    for name in ("rl-reserved.jsonl", "sft.jsonl", "validation.jsonl"):
        shutil.copy2(release / "dataset" / name, inputs / name)
    environments = inputs / "environments.json"
    shutil.copy2(plan["source_environments"], environments)
    from proof_eval.training.imports import restore_imports

    stage(plan, "restore_original_imports", model_calls=0)
    restore_imports(plan, root, home, inputs, environments)
    from proof_eval.training.prepare import prepare

    if plan.get("original_reference_seed"):
        from proof_eval.training.reference_seed import import_original_references

        imported = import_original_references(
            plan["original_reference_seed"], inputs, environments, root / "preparation"
        )
        immutable(home / "reference-import.json", imported)

    stage(plan, "prepare_originals", model_calls=0)
    result = prepare(
        inputs,
        environments,
        root / "preparation",
        Path(plan["harness_home"]) / "runtime/prompts/refactor_system.md",
        plan["episode_seconds"],
        workers=plan.get("reference_preparation_workers", 4),
        timeout_retries=plan.get("reference_timeout_retries", 0),
    )
    immutable(
        home / "prepared-summary.json",
        {k: v for k, v in result.items() if k != "records"},
    )
    require_preparation_policy(
        result["records"], plan.get("invalid_original_exclusions", [])
    )
    stage(
        plan,
        (
            "reuse_original_base_cache"
            if plan.get("base_model_cache")
            else "download_original_base"
        ),
        model=plan["model"],
        revision=plan["model_revision"],
    )
    # A separate finite download operation; failed download never starts training.
    cache_dir = Path(plan.get("base_model_cache", str(root / "model-cache")))
    download_code = (
        "from huggingface_hub import snapshot_download; "
        f"print(snapshot_download(repo_id={plan['model']!r},revision={plan['model_revision']!r},"
        f"cache_dir={str(cache_dir)!r},local_files_only={bool(plan.get('base_model_cache'))!r},max_workers=4),flush=True)"
    )
    env = {**os.environ, "HF_HUB_DOWNLOAD_TIMEOUT": "60", "HF_HUB_ETAG_TIMEOUT": "15"}
    downloaded = subprocess.run(
        [sys.executable, "-c", download_code],
        env=env,
        text=True,
        capture_output=True,
        timeout=7200,
    )
    (root / "model-download.log").write_text(
        downloaded.stdout + "\n" + downloaded.stderr
    )
    downloaded.check_returncode()
    model_path = Path(downloaded.stdout.strip().splitlines()[-1])
    if (
        model_path.name != plan["model_revision"]
        or sha(model_path / "config.json") != plan["model_config_sha256"]
    ):
        raise RuntimeError(
            "Downloaded model revision/config differs from the original base"
        )
    immutable(
        root / "model-identity.json",
        {
            "model": plan["model"],
            "revision": plan["model_revision"],
            "path": str(model_path),
            "config_sha256": sha(model_path / "config.json"),
        },
    )
    from proof_eval.training.context import admit_prepared
    from proof_eval.training.recovery import consumed_tasks

    admission = admit_prepared(
        root / "preparation",
        model_path,
        plan["context_tokens"],
        plan["per_turn_max_tokens"],
        exclude_started=consumed_tasks(plan),
    )
    from proof_eval.training.checkpoint_resume import prepare_remaining_resume

    resumed = prepare_remaining_resume(plan, admission)
    if resumed:
        immutable(home / "original-template-admission.json", admission)
        admission = {
            **admission,
            "template_train_sha256": admission["train_sha256"],
            "train_sha256": resumed["train_sha256"],
            "training_rows": resumed["training_rows"],
            "distinct_eligible_tasks": resumed["distinct_eligible_tasks"],
            "resume_prior_trained_tasks": resumed["prior_trained_tasks"],
            "resume_prior_unupdated_policy_tasks": resumed[
                "prior_unupdated_policy_tasks"
            ],
            "resumed_optimizer_iteration": resumed["resumed_optimizer_iteration"],
            "global_train_iters": resumed["global_train_iters"],
        }
    immutable(home / "context-admission.json", admission)
    config = {
        **plan,
        "prepared": str(root / "preparation"),
        "dataset": str(inputs / "rl-reserved.jsonl"),
        "rollout_root": str(root / "rollouts"),
        "system_prompt": str(
            Path(plan["harness_home"]) / "runtime/prompts/refactor_system.md"
        ),
    }
    config["semantic_config"] = tools["semantic_config"]
    config["web_config"] = tools["web_config"]
    from proof_eval.training import tool_broker

    config["cpu_tool_broker"] = tool_broker.broker_spec(plan, root, home)
    immutable(root / "rl-config.json", config)
    cpu_tools = tool_broker.start(root / "rl-config.json")
    env.update(
        {
            "PYTHONPATH": str(release / "src"),
            "ARENA_RL_CONFIG": str(root / "rl-config.json"),
            "ARENA_RL_RUN_PURPOSE": plan.get("purpose", "arena_direct_rl"),
            "ARENA_RL_TOKEN_ROOT": str(root / "exact-model-io"),
            "ARENA_RL_OPTIMIZER_ROOT": str(root / "optimizer-steps"),
            "ARENA_RL_OPTIMIZER_HOME": str(home / "optimizer-steps"),
            "ARENA_RL_CHECKPOINT_HOME": str(home / "checkpoint-receipts"),
            "PLE_CPU_OFFLOAD": "1",
            "NPROC_PER_NODE": "8",
            "PYTHONNOUSERSITE": "1",
            "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
            "HF_HUB_OFFLINE": "1",
            "TOKENIZERS_PARALLELISM": "false",
        }
    )
    command = training_command(plan, str(model_path))
    immutable(root / "training-command.json", command)
    stage(
        plan,
        "training_starting",
        eligible_tasks=admission["distinct_eligible_tasks"],
        configured_context_tokens=plan["context_tokens"],
        actual_long_context_capacity="not_yet_measured",
        expected_steps=admission["training_rows"] * 4 // 8,
        tuner_type="lora",
        full_parameter_training=False,
        resumed_optimizer_iteration=(resumed or {}).get(
            "resumed_optimizer_iteration", 0
        ),
        global_target_updates=(resumed or {}).get(
            "global_train_iters", admission["training_rows"] * 4 // 8
        ),
    )
    with (root / "training.log").open("x") as log:
        child = subprocess.Popen(
            command, env=env, stdout=log, stderr=subprocess.STDOUT, cwd=release
        )
        immutable(
            home / "trainer-process.json",
            {
                "pid": child.pid,
                "start_ticks": Path(f"/proc/{child.pid}/stat")
                .read_text()
                .rsplit(")", 1)[1]
                .split()[19],
                "at_epoch": time.time(),
                "command_sha256": sha(root / "training-command.json"),
            },
        )
        code = child.wait()
    if code:
        mirror_trainer_exit(root, home, code, release / "plan.json")
    tool_broker.stop(config, cpu_tools)
    if code:
        raise RuntimeError(
            f"Trainer exited {code}; preserve its exact logs and checkpoints, no automatic replay"
        )
    steps = list((root / "optimizer-steps").glob("rank-*/step-*.json"))
    updates = [read(p) for p in steps]
    if not any(
        x["update_successful"]
        and x["sampled_parameters_changed"]
        and x["grad_norm"] > 0
        for x in updates
    ):
        raise RuntimeError("Trainer ended without evidence of a parameter update")
    checkpoints = sorted(
        (root / "checkpoints").glob("checkpoint-*"),
        key=lambda p: int(p.name.split("-")[-1]),
    )
    if not checkpoints:
        raise RuntimeError("No durable training checkpoint")
    last = checkpoints[-1]
    files = {}
    for path in sorted(last.rglob("*")):
        if path.is_file():
            files[str(path.relative_to(last))] = {
                "bytes": path.stat().st_size,
                "sha256": sha(path),
            }
    finished = {
        "status": "training_completed",
        "at_epoch": time.time(),
        "checkpoint": str(last),
        "checkpoint_files": files,
        "optimizer_receipts": len(steps),
        "model": plan["model"],
        "model_revision": plan["model_revision"],
        "eligible_tasks": admission["distinct_eligible_tasks"],
        "prior_optimizer_trained_tasks": (resumed or {}).get("prior_trained_tasks", []),
        "prior_unupdated_policy_tasks": (resumed or {}).get(
            "prior_unupdated_policy_tasks", []
        ),
        "training_mode": "GRPO LoRA",
        "heldout_performance": "not_yet_evaluated",
    }
    immutable(root / "finished.json", finished)
    immutable(home / "finished.json", finished)
    stage(plan, "training_completed", checkpoint=str(last))
