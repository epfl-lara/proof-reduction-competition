"""ms-swift 4.6 external plugin: verified score GRPO with Arena tools."""

from __future__ import annotations

import asyncio
import hashlib
import math
import os
import time
import traceback
import uuid
from pathlib import Path

from swift.rewards import ORM, orms
from swift.rollout.multi_turn import MultiTurnScheduler, multi_turns

from proof_eval.evidence.immutable import immutable, read, sha
from proof_eval.training.remote_episode import RemoteEpisode as Episode
from proof_eval.training.reward import UnscorableEpisode, validate_token_evidence
from proof_eval.training.shutdown import install_colocated_shutdown


class ArenaScheduler(MultiTurnScheduler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = read(os.environ["ARENA_RL_CONFIG"])
        self.episodes = {}
        self.trajectory_failures = []

    def _record_failure(self, request, phase, error):
        record = {
            "task_id": request.data_dict["arena_task_id"],
            "uuid": request.uuid,
            "rank": int(os.environ.get("RANK", "0")),
            "phase": phase,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "at_epoch": time.time(),
            "reward_assigned": False,
            "automatic_model_replay": False,
        }
        rank = "rank-" + str(record["rank"])
        name = request.uuid + "-" + phase + ".json"
        root = Path(self.config["rollout_root"]).parent
        pin = immutable(root / "episode-failures" / rank / name, record)
        if self.config.get("home"):
            immutable(
                Path(self.config["home"]) / "episode-failures" / rank / name, record
            )
        self.trajectory_failures.append(
            {
                k: record[k]
                for k in ("task_id", "uuid", "rank", "phase", "error_type", "error")
            }
        )
        return {
            "done": True,
            "rollout_infos": {
                "arena_unscorable": True,
                "error_receipt_sha256": pin,
                "task_id": record["task_id"],
                "num_turns": getattr(self.episodes.get(request.uuid), "turns", 0),
            },
        }

    async def on_trajectory_start(self, requests):
        from proof_eval.training.coordinated_failure import gather_failures

        rank = int(os.environ.get("RANK", "0"))
        self.trajectory_failures = []
        for req in requests:
            try:
                if req.uuid in self.episodes:
                    raise UnscorableEpisode("Duplicate rollout UUID; do not replay")
                episode = await asyncio.to_thread(
                    Episode, req.data_dict["arena_task_id"], req.uuid, rank, self.config
                )
                req.messages = episode.initial_messages()
                self.episodes[req.uuid] = episode
            except Exception as error:
                self._record_failure(req, "original-start", error)
        failed = gather_failures(self.trajectory_failures)
        if failed:
            raise UnscorableEpisode(
                "Original setup failed on a rollout rank: " + str(failed)
            )

    async def on_turn_end(self, infer_request, response_choice, current_turn):
        try:
            return await self._on_turn_end(infer_request, response_choice, current_turn)
        except Exception as error:
            return self._record_failure(
                infer_request, "turn-" + str(current_turn), error
            )

    async def _on_turn_end(self, infer_request, response_choice, current_turn):
        ids = list(response_choice.token_ids or [])
        raw = response_choice.logprobs or {}
        logprobs = [r["logprob"] for r in raw.get("content", [])]
        validate_token_evidence(ids, logprobs)
        episode = self.episodes[infer_request.uuid]
        if current_turn != episode.turns + 1:
            raise UnscorableEpisode("Turn ordering changed")
        result = await asyncio.to_thread(
            episode.advance,
            response_choice.message.content,
            response_choice.finish_reason,
            {
                "task_id": infer_request.data_dict["arena_task_id"],
                "sampled_token_ids": ids,
                "behavior_logprobs": logprobs,
                "actual_input_messages": infer_request.messages,
            },
        )
        # End before the next request could overflow; never silently truncate a context.
        if not result["done"]:
            next_messages = [
                *infer_request.messages,
                {"role": "user", "content": episode.next_observation()},
            ]
            # Inspect without applying the trainer's truncation policy.
            from copy import copy

            template = copy(self._template)
            template.max_length = None
            encoded = template.encode(
                {
                    "messages": next_messages,
                    "chat_template_kwargs": infer_request.chat_template_kwargs,
                },
                return_length=True,
            )
            length = len(encoded["input_ids"])
            if (
                length + self.config["per_turn_max_tokens"] + 64
                > self.config["context_tokens"]
            ):
                result["done"] = True
                result["rollout_infos"][
                    "stop_reason"
                ] = "context_budget_before_overflow"
                result["rollout_infos"]["reward_receipt_sha256"] = immutable(
                    episode.folder / "reward.json",
                    result["rollout_infos"],
                )
        if result["done"]:
            self.episodes.pop(infer_request.uuid).close()
        return result

    def step(self, infer_request, response_choice, current_turn):
        episode = self.episodes[infer_request.uuid]
        infer_request.messages.append(
            {"role": "user", "content": episode.next_observation()}
        )
        return {"infer_request": infer_request}


class ArenaReward(ORM):
    def __call__(self, completions, rollout_infos, **kwargs):
        if len(completions) != len(rollout_infos):
            raise UnscorableEpisode("Reward/sample cardinality changed")
        values = []
        for info in rollout_infos:
            path = Path(info["episode_path"]) / "reward.json"
            if sha(path) != info["reward_receipt_sha256"]:
                raise UnscorableEpisode("Host reward receipt changed")
            receipt = read(path)
            if receipt["arena_reward"] != info["arena_reward"]:
                raise UnscorableEpisode("Sample reward differs from host receipt")
            values.append(receipt["arena_reward"])
        return values


orms["arena_score_gain"] = ArenaReward
multi_turns["arena_tools"] = ArenaScheduler


def install_exact_token_capture():
    """Observe actual engine inputs/outputs without re-tokenizing decoded text."""
    from swift.infer_engine.grpo_vllm_engine import GRPOVllmEngine

    old = GRPOVllmEngine._create_chat_completion_response
    if getattr(old, "arena_token_capture", False):
        return

    def capture(self, result, inputs, request_config, request_id):
        if POLICY_STEP is None:
            raise UnscorableEpisode("No observed rollout weight version")
        response = old(self, result, inputs, request_config, request_id)
        folder = (
            Path(os.environ["ARENA_RL_TOKEN_ROOT"])
            / f"rank-{os.environ.get('RANK', '0')}"
        )
        record = {
            "request_id": request_id,
            "purpose": (
                os.environ.get("ARENA_RL_RUN_PURPOSE")
                or (
                    "synthetic_gpu_smoke_only"
                    if GPU_PROBE_ACTIVE
                    else "arena_training_rollout"
                )
            ),
            "at_epoch": time.time(),
            "prompt_token_ids": list(result.prompt_token_ids),
            "choices": [],
            "policy_step": POLICY_STEP,
        }
        for output, choice in zip(result.outputs, response.choices):
            lps = [x["logprob"] for x in (choice.logprobs or {}).get("content", [])]
            ids = list(output.token_ids)
            validate_token_evidence(ids, lps)
            record["choices"].append(
                {
                    "sampled_token_ids": ids,
                    "behavior_logprobs": lps,
                    "finish_reason": output.finish_reason,
                    "decoded_response": choice.message.content,
                }
            )
        immutable(folder / (uuid.uuid4().hex + ".json"), record)
        return response

    capture.arena_token_capture = True
    GRPOVllmEngine._create_chat_completion_response = capture


POLICY_STEP = None
GPU_PROBE_ACTIVE = False


def install_policy_version_capture():
    from swift.megatron.trainers.rollout_mixin import MegatronRolloutMixin

    old = MegatronRolloutMixin._move_model_to_vllm
    if getattr(old, "arena_policy_capture", False):
        return

    def move(self):
        global POLICY_STEP
        result = old(self)
        POLICY_STEP = int(self._step)
        return result

    move.arena_policy_capture = True
    MegatronRolloutMixin._move_model_to_vllm = move


install_exact_token_capture()
install_policy_version_capture()


def install_optimizer_receipts():
    from swift.megatron.trainers.base import BaseMegatronTrainer

    old = BaseMegatronTrainer.train_step
    if getattr(old, "arena_optimizer_capture", False):
        return

    def sample_hash(trainer):
        digest = hashlib.sha256()
        count = 0
        for model in trainer.unwrapped_models:
            for name, parameter in model.named_parameters():
                if parameter.requires_grad:
                    # Include both A and B tensors; A can have zero gradient at initialization.
                    values = parameter.detach().reshape(-1)[:256].float().cpu().numpy()
                    digest.update(name.encode())
                    digest.update(values.tobytes())
                    count += 1
                    if count >= 32:
                        return digest.hexdigest()
        if not count:
            raise UnscorableEpisode("Trainer has no trainable parameters")
        return digest.hexdigest()

    def train_step(self, train_data_iterator):
        before = sample_hash(self)
        result = old(self, train_data_iterator)
        _, norm, successful = result
        norm = float(norm)
        if not math.isfinite(norm):
            raise UnscorableEpisode("Optimizer returned a non-finite gradient norm")
        after = sample_hash(self)
        record = {
            "purpose": os.environ.get("ARENA_RL_RUN_PURPOSE", "arena_direct_rl"),
            "optimizer_step": self.state.iteration + 1,
            "at_epoch": time.time(),
            "update_successful": bool(successful),
            "grad_norm": norm,
            "trainable_sample_before_sha256": before,
            "trainable_sample_after_sha256": after,
            "sampled_parameters_changed": before != after,
        }
        relative = f"rank-{os.environ.get('RANK', '0')}/step-{self.state.iteration + 1:06d}.json"
        for variable in ("ARENA_RL_OPTIMIZER_ROOT", "ARENA_RL_OPTIMIZER_HOME"):
            immutable(Path(os.environ[variable]) / relative, record)
        return result

    train_step.arena_optimizer_capture = True
    BaseMegatronTrainer.train_step = train_step


install_optimizer_receipts()


def install_loss_token_gate():
    from swift.megatron.trainers import grpo_trainer
    from swift.rlhf_trainers import utils

    from proof_eval.training.fidelity import check_loss_tokens

    old = utils.encode_sample
    if getattr(old, "arena_loss_token_gate", False):
        return

    def encode(sample, template, *, encode_prompt_only=False):
        result = old(sample, template, encode_prompt_only=encode_prompt_only)
        if not encode_prompt_only:
            check_loss_tokens(
                sample.response_token_ids, sample.response_loss_mask, result
            )
        return result

    encode.arena_loss_token_gate = True
    utils.encode_sample = encode
    grpo_trainer.encode_sample = encode


def install_early_checkpoint_receipts():
    from swift.megatron.trainers.base import BaseMegatronTrainer

    old_event = BaseMegatronTrainer.call_event
    old_save = BaseMegatronTrainer.save_checkpoint
    if getattr(old_event, "arena_early_checkpoint", False):
        return

    def event(self, name, *args, **kwargs):
        result = old_event(self, name, *args, **kwargs)
        if name == "on_step_end" and self.state.iteration in (1, 2):
            self.state.should_save = True
        return result

    def save(self):
        result = old_save(self)
        if int(os.environ.get("RANK", "0")) == 0:
            folder = Path(self.state.last_model_checkpoint)
            files = {
                p.name: {"bytes": p.stat().st_size, "sha256": sha(p)}
                for p in sorted(folder.glob("*"))
                if p.is_file()
            }
            immutable(
                Path(os.environ["ARENA_RL_CHECKPOINT_HOME"])
                / f"step-{self.state.iteration:06d}.json",
                {
                    "purpose": os.environ.get(
                        "ARENA_RL_RUN_PURPOSE", "arena_direct_rl"
                    ),
                    "step": self.state.iteration,
                    "at_epoch": time.time(),
                    "checkpoint": str(folder),
                    "files": files,
                },
            )
        return result

    event.arena_early_checkpoint = True
    BaseMegatronTrainer.call_event = event
    BaseMegatronTrainer.save_checkpoint = save


install_loss_token_gate()
install_early_checkpoint_receipts()

install_colocated_shutdown()


def install_coordinated_rollout_failure():
    from swift.megatron.trainers.rollout_mixin import MegatronRolloutMixin

    from proof_eval.training.coordinated_failure import gather_failures

    old = MegatronRolloutMixin._rollout_requests
    if getattr(old, "arena_coordinated_failure", False):
        return

    def rollout_requests(self, requests, request_config):
        global GPU_PROBE_ACTIVE
        scheduler = getattr(self, "multi_turn_scheduler", None)
        failures = gather_failures(getattr(scheduler, "trajectory_failures", []))
        if failures:
            raise UnscorableEpisode(
                "Rollout tool failure; no rewards or update: " + str(failures)
            )
        config = getattr(scheduler, "config", {})
        if config.get("gpu_runtime_probe") and not getattr(
            self, "arena_gpu_probed", False
        ):
            from swift.infer_engine.protocol import RolloutInferRequest

            from proof_eval.training.gpu_probe import run_probe

            active = self.engine.engine.vllm_config
            observed = {
                "enforce_eager": active.model_config.enforce_eager,
                "enable_prefix_caching": active.cache_config.enable_prefix_caching,
                "context_tokens": active.model_config.max_model_len,
            }
            if observed != {
                "enforce_eager": config["vllm_enforce_eager"],
                "enable_prefix_caching": config["vllm_prefix_caching"],
                "context_tokens": config["context_tokens"],
            }:
                raise UnscorableEpisode(
                    "Actual GPU engine differs from the declared plan"
                )
            GPU_PROBE_ACTIVE = True
            try:
                run_probe(
                    lambda reqs, options: old(self, reqs, options),
                    request_config,
                    RolloutInferRequest,
                    {**config, "observed_gpu_engine": observed},
                    int(os.environ.get("RANK", "0")),
                    gather_failures,
                )
            finally:
                GPU_PROBE_ACTIVE = False
            self.arena_gpu_probed = True
        return old(self, requests, request_config)

    rollout_requests.arena_coordinated_failure = True
    MegatronRolloutMixin._rollout_requests = rollout_requests


install_coordinated_rollout_failure()

if os.environ.get("ARENA_RL_RUN_PURPOSE") == "synthetic_gpu_training_check":
    from proof_eval.training.gpu_training_probe import register

    register()
