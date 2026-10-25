"""Host-owned rollout state; no import-time model, Lean, or file operations."""

from __future__ import annotations

import json
import time
from pathlib import Path

from proof_eval.evidence.immutable import immutable, read, sha
from proof_eval.training.actions import initial_messages, parse_action
from proof_eval.training.reward import ScorePotential, UnscorableEpisode
from proof_eval.training.session import TrainingProofSession


class Episode:
    def __init__(self, task_id: str, uuid: str, rank: int, config: dict):
        from proof_eval import Evaluator
        from proof_eval.verification.initial import measure_original, private_evaluator
        from proof_eval.verification.references import (
            REFERENCE_FIELDS,
            required_versions,
        )

        prepared = Path(config["prepared"])
        index = read(prepared / "prepared.json")
        entry = next(r for r in index["records"] if r["task_id"] == task_id)
        if (
            entry["status"] != "prepared"
            or sha(prepared / entry["pack_path"]) != entry["pack_sha256"]
        ):
            raise UnscorableEpisode("Task did not pass original reference preparation")
        self.pack = read(prepared / entry["pack_path"])
        self.versions = required_versions(self.pack)
        self.folder = Path(config["rollout_root"]) / f"rank-{rank}" / uuid
        self.folder.mkdir(parents=True, exist_ok=False)
        self.started = time.monotonic()
        self.config, self.turns = config, 0
        immutable(
            self.folder / "started.json",
            {
                "task_id": task_id,
                "task": entry["task"],
                "uuid": uuid,
                "rank": rank,
                "at_epoch": time.time(),
                "pack_sha256": entry["pack_sha256"],
                "seconds": config["episode_seconds"],
                "history": False,
                "transport": "Arena training ReAct; host tool API; not native Lemex",
            },
        )
        originals = Evaluator(
            config["dataset"],
            index["environments"],
            prepared / "cache",
            timeout=300,
        )
        # These are local original reference values, never another rollout's solution.
        current = originals.get_reference(self.pack["name"])["versions"]
        for version in self.versions:
            expected = self.pack["incumbent"]["per_version"][version]["reference"]
            if current[version].get("status") != "prepared" or any(
                current[version].get(field) != expected.get(field)
                for field in REFERENCE_FIELDS
            ):
                raise UnscorableEpisode(
                    "Original environment/reference fingerprint changed"
                )
        self.evaluator = private_evaluator(originals, self.folder, self.pack)
        _, original = measure_original(self.evaluator, self.folder, self.pack)
        if time.monotonic() - self.started >= config["episode_seconds"]:
            raise UnscorableEpisode("Original measurement exhausted the episode budget")
        self.session = TrainingProofSession(
            self.folder / "evidence",
            self.pack,
            self.evaluator,
            "score_edges",
            cleanup=None,
            restart_scope=None,
            semantic_config=config["semantic_config"],
            web_config=config["web_config"],
            original_measurement=original,
        )
        self.potential = ScorePotential.from_original(
            self.session.original, self.versions
        )
        self.pending_observation = None

    def initial_messages(self) -> list[dict]:
        system = Path(self.config["system_prompt"]).read_text()
        return initial_messages(
            {**self.pack, "incumbent": self.session.best_evaluation},
            system,
            max(0, self.config["episode_seconds"] - (time.monotonic() - self.started)),
        )

    def advance(self, completion: str, finish_reason: str, token_record: dict) -> dict:
        self.turns += 1
        immutable(
            self.folder / "turns" / f"{self.turns:04d}-model.json",
            {
                "completion": completion,
                "finish_reason": finish_reason,
                **token_record,
            },
        )
        done, reason = False, None
        if finish_reason == "length":
            # A generation cap is an explicit on-policy boundary, not an invented failure score.
            done, reason = True, "per_turn_generation_limit"
        else:
            try:
                action = parse_action(completion)
            except (ValueError, TypeError) as error:
                observation = {"kind": "invalid_action", "error": str(error)}
            else:
                immutable(
                    self.folder / "turns" / f"{self.turns:04d}-tool-started.json",
                    action,
                )
                try:
                    observation = self.session.dispatch(action)
                except (
                    ValueError,
                    FileNotFoundError,
                    IsADirectoryError,
                    KeyError,
                    TypeError,
                ) as error:
                    observation = {"kind": "tool_argument_error", "error": str(error)}
                # An unavailable verifier does not look like ordinary candidate rejection.
                for check in self.session.checks:
                    evaluation = check["evaluation"]
                    if evaluation.get("status") in {"incomplete", "unavailable"}:
                        raise UnscorableEpisode(
                            "A candidate lacked authoritative verifier evidence"
                        )
                immutable(
                    self.folder / "turns" / f"{self.turns:04d}-tool-result.json",
                    observation,
                )
                done = action["op"] == "finish"
                reason = "agent_finish" if done else None
            self.pending_observation = observation
        delta = self.potential.observe_best(self.session.best_evaluation, self.versions)
        if (
            not done
            and time.monotonic() - self.started >= self.config["episode_seconds"]
        ):
            done, reason = True, "episode_time_budget"
        if not done and self.turns >= self.config["max_turns"]:
            done, reason = True, "max_turns"
        info = {
            "arena_reward": self.potential.reward,
            "best_score": self.potential.best,
            "original_score": self.potential.original,
            "delta_best_score": delta,
            "task_id": token_record["task_id"],
            "episode_path": str(self.folder),
            "num_turns": self.turns,
            "reward_authority": "host_ProofSession",
        }
        if done:
            info["stop_reason"] = reason
            info["reward_receipt_sha256"] = immutable(self.folder / "reward.json", info)
        return {"done": done, "rollout_infos": info}

    def next_observation(self) -> str:
        return json.dumps(self.pending_observation, ensure_ascii=False, allow_nan=False)
