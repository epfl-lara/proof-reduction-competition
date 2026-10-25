"""Lightweight training-side proxy; all proof/session work stays in the CPU service."""

from pathlib import Path

from proof_eval.training.tool_broker import rpc


class RemoteEpisode:
    def __init__(self, task_id, uuid, rank, config):
        self.config, self.uuid, self.rank = config, uuid, str(rank)
        value = rpc(config, self.rank, uuid, "create", {"task_id": task_id})
        self.folder, self.turns = Path(value["folder"]), value["turns"]
        self.messages = value["messages"]
        self.pending = None

    def initial_messages(self):
        return self.messages

    def advance(self, completion, finish_reason, token_record):
        value = rpc(
            self.config,
            self.rank,
            self.uuid,
            "advance",
            {
                "completion": completion,
                "finish_reason": finish_reason,
                "token_record": token_record,
            },
        )
        self.turns, self.pending = value["turns"], value["next_observation"]
        return value["result"]

    def next_observation(self):
        return self.pending

    def close(self):
        return rpc(self.config, self.rank, self.uuid, "close", {})
