"""Regression coverage for the observed missing-FA2 and lost-exit-log failure."""

import hashlib
import sys

from proof_eval.training.command import training_command
from proof_eval.training.runner import mirror_trainer_exit


def test_launcher_preserves_interpreter_and_selects_installed_attention_backends():
    plan = {
        "root": "/scratch/new",
        "home": "/home/new",
        "context_tokens": 32768,
        "model_revision": "original",
        "per_turn_max_tokens": 8192,
        "max_turns": 32,
        "attention_backend": "fused",
        "vit_attn_impl": "sdpa",
        "checkpoint_every_updates": 1,
    }
    command = training_command(plan, "/cache/original")
    assert command[:4] == [sys.executable, "-m", "swift.cli._megatron.main", "rlhf"]
    assert command[command.index("--attention_backend") + 1] == "fused"
    assert command[command.index("--vit_attn_impl") + 1] == "sdpa"
    assert command[command.index("--max_length") + 1] == "32768"
    assert command[command.index("--save_steps") + 1] == "1"


def test_failed_trainer_tail_survives_without_a_running_container(tmp_path):
    root, home = tmp_path / "scratch", tmp_path / "home"
    root.mkdir()
    home.mkdir()
    raw = b"prefix" * 30000 + b"\nImportError: missing optional attention\n\xff"
    (root / "training.log").write_bytes(raw)
    plan = tmp_path / "plan.json"
    plan.write_text('{"model":"original"}')
    record = mirror_trainer_exit(root, home, 1, plan)
    assert (home / "trainer-exit.json").is_file()
    assert record["tail_sha256"] == hashlib.sha256(raw[-128 * 1024 :]).hexdigest()
    assert record["tail_offset"] + len(raw[-128 * 1024 :]) == len(raw)
    assert "ImportError: missing optional attention" in record["tail_utf8"]
    assert (root / "training.log").read_bytes() == raw
