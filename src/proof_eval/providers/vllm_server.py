"""Pinned vLLM launch settings and owned server lifecycle for local experiments."""

from __future__ import annotations

import fcntl
import json
import os
import socket
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from proof_eval.defaults import LOCAL_QWEN_WORKERS, QWEN_CONTEXT_TOKENS
from proof_eval.evidence.io import digest, now, write_json

from .lemex_local import MODEL
from .processes import stop_tree

REVISION = "236dfdf285828023ca3bcd3f37366c58a3469b13"
RCP_API_HF_OVERRIDES = {
    "text_config": {
        "rope_parameters": {
            "mrope_interleaved": True,
            "mrope_section": [11, 11, 10],
            "rope_type": "yarn",
            "rope_theta": 10000000,
            "partial_rotary_factor": 0.25,
            "factor": 4.0,
            "original_max_position_embeddings": 262144,
        }
    }
}


@dataclass(frozen=True)
class ServerConfig:
    mode: str = "mtp3"
    port: int = 8128
    binary: str = "vllm"
    python: str = sys.executable
    model_cache: str = str(Path.home() / ".cache/huggingface")
    model: str = MODEL
    revision: str = REVISION
    startup_seconds: float = 1200
    execution_mode: str = "compiled"
    profile: str = "rcp-api-flags"
    max_model_len: int = QWEN_CONTEXT_TOKENS
    max_num_seqs: int = LOCAL_QWEN_WORKERS
    gpu_memory_utilization: float = 0.95

    def __post_init__(self):
        if self.model != MODEL and self.revision == REVISION:
            raise ValueError("Select an exact revision for a different model")
        if self.mode not in ("baseline", "mtp3") or not 0 < self.port < 65536:
            raise ValueError("Invalid local vLLM mode or port")
        if self.execution_mode not in ("eager", "compiled"):
            raise ValueError("execution_mode must be eager or compiled")
        if self.profile not in ("historical", "rcp-api-flags"):
            raise ValueError("Unknown server profile")
        if (
            type(self.max_model_len) is not int
            or not 1024 <= self.max_model_len <= 1048576
        ):
            raise ValueError("max_model_len must be an integer in [1024, 1048576]")
        if self.max_model_len > 262144 and self.profile != "rcp-api-flags":
            raise ValueError("Extended context requires the rcp-api-flags YaRN profile")
        if type(self.max_num_seqs) is not int or self.max_num_seqs < 1:
            raise ValueError("max_num_seqs must be a positive integer")
        if (
            isinstance(self.gpu_memory_utilization, bool)
            or not 0 < self.gpu_memory_utilization < 1
        ):
            raise ValueError("gpu_memory_utilization must be between zero and one")

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"


def command(config: ServerConfig) -> list[str]:
    """The paired commands differ only in the MTP3 speculative configuration."""
    argv = [
        config.binary,
        "serve",
        config.model,
        "--revision",
        config.revision,
        "--tokenizer-revision",
        config.revision,
        "--host",
        "127.0.0.1",
        "--port",
        str(config.port),
        "--tensor-parallel-size",
        "4",
        "--enable-expert-parallel",
        "--max-model-len",
        str(config.max_model_len),
        "--max-num-seqs",
        str(config.max_num_seqs),
        "--max-num-batched-tokens",
        "8192",
        "--gpu-memory-utilization",
        (
            "0.90"
            if config.gpu_memory_utilization == 0.90
            else str(config.gpu_memory_utilization)
        ),
        "--language-model-only",
        "--reasoning-parser",
        "qwen3",
        "--default-chat-template-kwargs",
        json.dumps(
            {
                "enable_thinking": True,
                "preserve_thinking": True,
                "reasoning_effort": "xhigh",
            }
        ),
        "--engram-config",
        json.dumps({"cpu_offload": True}),
        "--enable-auto-tool-choice",
        "--tool-call-parser",
        "qwen3_xml" if config.profile == "rcp-api-flags" else "qwen3_coder",
    ]
    if config.profile == "rcp-api-flags":
        argv += [
            "--enable-prompt-tokens-details",
            "--moe-backend",
            "marlin",
            "--prefix-cache-retention-interval",
            "800",
            "--hf-overrides",
            json.dumps(RCP_API_HF_OVERRIDES),
            "--served-model-name",
            config.model,
        ]
    else:
        argv += ["--override-generation-config", json.dumps({"max_new_tokens": 32768})]
    if config.execution_mode == "eager":
        argv += ["--enforce-eager"]
    if config.mode == "mtp3":
        argv += [
            "--speculative-config",
            json.dumps({"method": "mtp", "num_speculative_tokens": 3}),
        ]
    return argv


def environment(config: ServerConfig, plugin: Path) -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        HF_HOME=config.model_cache,
        HF_HUB_CACHE=str(Path(config.model_cache) / "hub"),
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        VLLM_LOGGING_LEVEL="INFO",
        PYTHONPATH=str(plugin)
        + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""),
    )
    if config.profile == "rcp-api-flags":
        env["VLLM_ALLOW_LONG_MAX_MODEL_LEN"] = "1"
    return env


def metadata(config: ServerConfig, plugin: Path) -> dict:
    versions = subprocess.check_output(
        [
            config.python,
            "-c",
            "import importlib.metadata,json; print(json.dumps({k:importlib.metadata.version(k) for k in ('vllm','torch','transformers')}))",
        ],
        text=True,
    )
    return {
        "schema_version": 1,
        "config": asdict(config),
        "argv": command(config),
        "versions": json.loads(versions),
        "plugin_sha256": {
            str(p.relative_to(plugin)): digest(p)
            for p in sorted(plugin.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts
        },
    }


class ManagedServer:
    """Hold the GPU-server lock, collect raw metrics, and stop only owned children."""

    def __init__(
        self, config: ServerConfig, folder: Path, plugin: Path, lock_path: Path
    ):
        self.config, self.folder, self.plugin, self.lock_path = (
            config,
            folder,
            plugin,
            lock_path,
        )
        self.process = None
        self.stop_metrics = threading.Event()
        self.thread = None

    def _metrics(self):
        index = 0
        while True:
            try:
                with urlopen(
                    self.config.endpoint.removesuffix("/v1") + "/metrics", timeout=5
                ) as response:
                    text = response.read().decode()
                path = self.metrics_folder / f"{index:06d}.txt"
                path.write_text(text)
                write_json(
                    path.with_suffix(".json"), {"at": now(), "sha256": digest(path)}
                )
            except (OSError, URLError):
                pass
            index += 1
            if self.stop_metrics.wait(30):
                return

    def __enter__(self):
        self.folder.mkdir(parents=True, exist_ok=True)
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = self.lock_path.open("a")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise ValueError(
                "Another local experiment owns the four-GPU server; run the two scripts sequentially"
            ) from None
        try:
            with socket.socket() as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                probe.bind(("127.0.0.1", self.config.port))
            manifest = metadata(self.config, self.plugin)
            path = self.folder / "server_manifest.json"
            if path.exists() and json.loads(path.read_text()) != manifest:
                raise ValueError(
                    "Frozen server configuration changed; choose a new experiment root"
                )
            write_json(path, manifest)
            stamp = str(time.time_ns())
            self.metrics_folder = self.folder / "server" / stamp / "metrics"
            self.metrics_folder.mkdir(parents=True)
            self.log = (self.metrics_folder.parent / "server.log").open("w")
            self.process = subprocess.Popen(
                command(self.config),
                env=environment(self.config, self.plugin),
                stdout=self.log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                pass_fds=(self.lock.fileno(),),
            )
            write_json(
                self.metrics_folder.parent / "process.json",
                {"pid": self.process.pid, "started_at": now()},
            )
            deadline = time.monotonic() + self.config.startup_seconds
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise RuntimeError(
                        "vLLM exited during startup; inspect " + str(self.log.name)
                    )
                try:
                    with urlopen(
                        self.config.endpoint + "/models", timeout=2
                    ) as response:
                        models = json.load(response)
                    if self.config.model in {m["id"] for m in models["data"]}:
                        self.thread = threading.Thread(
                            target=self._metrics, daemon=True
                        )
                        self.thread.start()
                        return self
                except (OSError, URLError):
                    pass
                time.sleep(2)
            raise TimeoutError("vLLM startup timed out; inspect " + str(self.log.name))
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.process is not None and self.process.poll() is None:
            try:
                with urlopen(
                    self.config.endpoint.removesuffix("/v1") + "/metrics", timeout=5
                ) as response:
                    (self.metrics_folder / "final.txt").write_bytes(response.read())
            except (OSError, URLError):
                pass
        self.stop_metrics.set()
        if self.thread is not None:
            self.thread.join(timeout=6)
        if self.process is not None and self.process.poll() is None:
            stop_tree(self.process.pid)
            self.process.wait(timeout=15)
        if hasattr(self, "log"):
            self.log.close()
        if hasattr(self, "lock"):
            self.lock.close()

    def __exit__(self, *_):
        self.close()
