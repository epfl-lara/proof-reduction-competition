"""RCP (EPFL inference cluster) client and chat harness.

Provides zero-dependency (stdlib-only) communication with OpenAI-compatible
inference endpoints hosted on EPFL's RCP cluster, configured using .env keys
(e.g., RCP_BASE_URL, RCP_API_KEY) so standard OpenAI subscriptions/Codex
tokens are never disturbed.

Supports:
- Model selection (DeepSeek V4.1, Qwen3.5, Qwen3.6, Qwen3.8, etc.)
- Reasoning / thinking controls (enable_thinking, reasoning_effort)
  with model-specific template mapping (e.g. DeepSeek V4.1 vs Qwen)
- Multi-turn stateful chat harness (session management, fork, undo, transcript)
- Optional drop-in OpenAI SDK client factory if openai package is installed
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

DEFAULT_RCP_BASE_URL = "https://inference.rcp.epfl.ch/v1"

# Well-known tested models on EPFL RCP
MODELS = {
    "deepseek-flash": "deepseek-ai/DeepSeek-V4.1-Flash",
    "qwen-397b": "Qwen/Qwen3.5-397B-A17B",
    "qwen-35b": "Qwen/Qwen3.6-35B-A3B",
    "qwen-27b": "Qwen/Qwen3.8-27B",
}

DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4.1-Flash"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_REASONING = True
DEFAULT_REASONING_EFFORT = "high"


def find_env_file(start_path: Optional[Union[str, Path]] = None) -> Optional[Path]:
    """Search for a .env file starting at start_path and walking up to git root."""
    current = Path(start_path).resolve() if start_path else Path.cwd().resolve()
    if current.is_file():
        current = current.parent

    for candidate_dir in [current, *current.parents]:
        candidate_file = candidate_dir / ".env"
        if candidate_file.is_file():
            return candidate_file
        if (candidate_dir / ".git").exists():
            break
    return None


def parse_env_file(path: Union[str, Path]) -> Dict[str, str]:
    """Parse key-value pairs from a .env file, supporting 'export KEY=VAL' and quotes."""
    env_vars: Dict[str, str] = {}
    path = Path(path)
    if not path.is_file():
        return env_vars

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            env_vars[key] = val
    return env_vars


def load_rcp_env(env_path: Optional[Union[str, Path]] = None) -> Tuple[str, str]:
    """Load RCP_BASE_URL and RCP_API_KEY from environment or .env file.

    Priority:
    1. os.environ['RCP_BASE_URL'] and os.environ['RCP_API_KEY']
    2. Fallbacks: os.environ['RCP_OPENAI_BASE_URL'], os.environ['RCP_OPENAI_API_KEY']
    3. Variables parsed from .env file

    Does NOT read or overwrite standard OPENAI_API_KEY / OPENAI_BASE_URL.
    """
    base_url = os.environ.get("RCP_BASE_URL") or os.environ.get("RCP_OPENAI_BASE_URL")
    api_key = os.environ.get("RCP_API_KEY") or os.environ.get("RCP_OPENAI_API_KEY")

    if not (base_url and api_key):
        env_file = Path(env_path) if env_path else find_env_file()
        if env_file and env_file.is_file():
            parsed = parse_env_file(env_file)
            if not base_url:
                base_url = parsed.get("RCP_BASE_URL") or parsed.get(
                    "RCP_OPENAI_BASE_URL"
                )
            if not api_key:
                api_key = parsed.get("RCP_API_KEY") or parsed.get("RCP_OPENAI_API_KEY")

    base_url = (base_url or DEFAULT_RCP_BASE_URL).rstrip("/")
    if not api_key:
        raise RuntimeError(
            "RCP_API_KEY is not set. Please set RCP_API_KEY in your .env file "
            "or export RCP_API_KEY='sk-...'. "
            "This key is separate from standard OPENAI_API_KEY."
        )

    return base_url, api_key


def normalize_model_name(model: str) -> str:
    """Allow shorthand aliases like 'deepseek-flash' or 'qwen-35b'."""
    normalized = model.strip().lower()
    if normalized in MODELS:
        return MODELS[normalized]
    # Check if suffix matches
    for key, full in MODELS.items():
        if normalized == full.lower():
            return full
    return model.strip()


def map_rcp_reasoning(
    model: str,
    reasoning: Optional[bool] = None,
    reasoning_effort: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Build chat_template_kwargs and extra_body for RCP thinking models.

    EPFL RCP runs LiteLLM/vLLM.
    - DeepSeek V4.1 expects chat_template_kwargs with:
        enable_thinking: bool
        reasoning_effort: 'low', 'high', 'xhigh', 'max', or int [1, 100]
    - Qwen hybrid models expect:
        enable_thinking: bool
    """
    effective_reasoning = DEFAULT_REASONING if reasoning is None else reasoning
    effort_str = (
        str(
            reasoning_effort
            if reasoning_effort is not None
            else DEFAULT_REASONING_EFFORT
        )
        .strip()
        .lower()
    )

    if (
        effort_str in {"off", "none", "false", "disabled"}
        or effective_reasoning is False
    ):
        thinking_enabled = False
    else:
        thinking_enabled = True

    chat_template_kwargs: Dict[str, Any] = {"enable_thinking": thinking_enabled}
    extra_body: Dict[str, Any] = {}

    model_lower = model.lower()
    is_deepseek = "deepseek" in model_lower
    is_qwen38 = "3.8" in model_lower

    if thinking_enabled:
        # Standardize input effort string
        normalized_effort = (
            effort_str
            if effort_str in {"low", "medium", "high", "xhigh", "max"}
            else DEFAULT_REASONING_EFFORT
        )

        if is_deepseek:
            # DeepSeek V4.1 accepts: 'low', 'high', 'xhigh', 'max' (rejects 'medium')
            mapped_effort = (
                "high"
                if normalized_effort in {"medium", "auto", ""}
                else normalized_effort
            )
            chat_template_kwargs["reasoning_effort"] = mapped_effort
            extra_body["reasoning_effort"] = mapped_effort
        elif is_qwen38:
            # Qwen 3.8 accepts: 'low', 'medium', 'xhigh' (rejects 'high')
            mapped_effort = (
                "xhigh"
                if normalized_effort in {"high", "max", "auto", ""}
                else normalized_effort
            )
            chat_template_kwargs["reasoning_effort"] = mapped_effort
            extra_body["reasoning_effort"] = mapped_effort
        else:
            # Other models (e.g. Qwen 3.5, 3.6, etc.)
            mapped_effort = normalized_effort
            chat_template_kwargs["reasoning_effort"] = mapped_effort
            extra_body["reasoning_effort"] = mapped_effort

    extra_body["chat_template_kwargs"] = chat_template_kwargs
    return chat_template_kwargs, extra_body


@dataclass
class RCPResponse:
    """Normalized response from RCP chat completion."""

    content: str
    reasoning_content: Optional[str] = None
    model: str = ""
    role: str = "assistant"
    finish_reason: Optional[str] = None
    usage: Dict[str, int] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def reasoning(self) -> Optional[str]:
        """Convenience alias for reasoning_content."""
        return self.reasoning_content

    def to_dict(self) -> Dict[str, Any]:
        """Convert to OpenAI-compatible message dict for subsequent history turns."""
        msg: Dict[str, Any] = {
            "role": self.role,
            "content": self.content,
        }
        if self.reasoning_content is not None:
            msg["reasoning_content"] = self.reasoning_content
        return msg

    def __str__(self) -> str:
        return self.content


class RCPClient:
    """Client for calling models on EPFL RCP inference cluster."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        env_path: Optional[Union[str, Path]] = None,
        default_model: str = DEFAULT_MODEL,
        default_temperature: float = DEFAULT_TEMPERATURE,
        default_reasoning: bool = DEFAULT_REASONING,
        default_reasoning_effort: str = DEFAULT_REASONING_EFFORT,
        timeout: float = 60.0,
    ):
        if api_key and base_url:
            self.base_url = base_url.rstrip("/")
            self.api_key = api_key
        else:
            loaded_url, loaded_key = load_rcp_env(env_path)
            self.base_url = (base_url or loaded_url).rstrip("/")
            self.api_key = api_key or loaded_key

        self.default_model = normalize_model_name(default_model)
        self.default_temperature = default_temperature
        self.default_reasoning = default_reasoning
        self.default_reasoning_effort = default_reasoning_effort
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "proof-reduction-competition/rcp-client",
        }

    def list_models(self, timeout: Optional[float] = None) -> List[str]:
        """Return available model IDs hosted on the RCP endpoint."""
        url = f"{self.base_url}/models"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return sorted([m["id"] for m in data.get("data", []) if "id" in m])
        except urllib.error.HTTPError as err:
            err_msg = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"RCP /models request failed with HTTP {err.code}: {err_msg}"
            ) from err
        except Exception as err:
            raise RuntimeError(f"RCP /models request error: {err}") from err

    def create_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        reasoning: Optional[bool] = None,
        reasoning_effort: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> RCPResponse:
        """Execute a chat completion request on RCP.

        Args:
            messages: List of message dicts (e.g. [{'role': 'user', 'content': '...'}])
            model: Model identifier or alias (defaults to self.default_model)
            reasoning: True to enable thinking/reasoning, False to disable (default: True)
            reasoning_effort: 'low', 'medium', 'high', 'xhigh', 'max', or 'off' (default: 'high')
            temperature: Sampling temperature (default: 0.3)
            max_tokens: Maximum tokens to generate (default 3072 if reasoning enabled, else 1024)
            extra_body: Additional provider kwargs
            timeout: Request timeout in seconds
            **kwargs: Additional parameters forwarded to the payload (top_p, stop, etc.)
        """
        model_name = normalize_model_name(model or self.default_model)
        effective_reasoning = self.default_reasoning if reasoning is None else reasoning
        effective_effort = (
            self.default_reasoning_effort
            if reasoning_effort is None
            else reasoning_effort
        )
        effective_temp = (
            self.default_temperature if temperature is None else temperature
        )

        chat_kwargs, auto_extra = map_rcp_reasoning(
            model=model_name,
            reasoning=effective_reasoning,
            reasoning_effort=effective_effort,
        )

        merged_extra = dict(auto_extra)
        if extra_body:
            merged_extra.update(extra_body)

        # Ensure chat_template_kwargs is top-level and in extra_body for vLLM/LiteLLM compatibility
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "chat_template_kwargs": chat_kwargs,
            "extra_body": merged_extra,
            "temperature": effective_temp,
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        else:
            # Thinking models consume token allowance during reasoning, so use a healthy default
            payload["max_tokens"] = 3072 if chat_kwargs.get("enable_thinking") else 1024

        payload.update(kwargs)

        url = f"{self.base_url}/chat/completions"
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data_bytes, headers=self._headers(), method="POST"
        )

        effective_timeout = timeout if timeout is not None else self.timeout
        try:
            with urllib.request.urlopen(req, timeout=effective_timeout) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            err_msg = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"RCP API HTTP {err.code} ({model_name}): {err_msg}"
            ) from err
        except urllib.error.URLError as err:
            raise RuntimeError(
                f"RCP network error connecting to {url}: {err.reason}"
            ) from err
        except Exception as err:
            raise RuntimeError(f"RCP request failure for {model_name}: {err}") from err

        choices = res_data.get("choices", [])
        if not choices:
            raise RuntimeError(
                f"RCP API returned empty choices for model {model_name}: {res_data}"
            )

        choice = choices[0]
        msg_obj = choice.get("message", {})
        raw_content = msg_obj.get("content")
        # Normalize content to string (vLLM can return None if max_tokens hit during reasoning)
        content = "" if raw_content is None else str(raw_content)

        reasoning_content = msg_obj.get("reasoning_content") or msg_obj.get("reasoning")
        finish_reason = choice.get("finish_reason")
        usage = res_data.get("usage", {})

        return RCPResponse(
            content=content,
            reasoning_content=reasoning_content,
            model=res_data.get("model", model_name),
            role=msg_obj.get("role", "assistant"),
            finish_reason=finish_reason,
            usage=usage,
            raw=res_data,
        )

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        reasoning: Optional[bool] = None,
        reasoning_effort: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> RCPResponse:
        """Convenience method for a single-turn prompt."""
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        return self.create_chat_completion(
            messages=messages,
            model=model,
            reasoning=reasoning,
            reasoning_effort=reasoning_effort,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    def chat_harness(
        self,
        system: Optional[str] = None,
        model: Optional[str] = None,
        reasoning: Optional[bool] = None,
        reasoning_effort: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> RCPChat:
        """Create a stateful multi-turn chat harness session."""
        return RCPChat(
            client=self,
            system=system,
            model=model or self.default_model,
            reasoning=self.default_reasoning if reasoning is None else reasoning,
            reasoning_effort=(
                self.default_reasoning_effort
                if reasoning_effort is None
                else reasoning_effort
            ),
            temperature=(
                self.default_temperature if temperature is None else temperature
            ),
            max_tokens=max_tokens,
        )

    def test_model(
        self,
        model: str,
        timeout: float = 30.0,
        enable_thinking: bool = False,
    ) -> Dict[str, Any]:
        """Test responsiveness of a single model with ping prompt."""
        model_name = normalize_model_name(model)
        start_t = time.time()
        try:
            resp = self.create_chat_completion(
                messages=[{"role": "user", "content": "Return the exact word: PONG"}],
                model=model_name,
                reasoning=enable_thinking,
                max_tokens=64,
                timeout=timeout,
            )
            elapsed = time.time() - start_t
            return {
                "model": model_name,
                "status": "ok",
                "elapsed_s": round(elapsed, 2),
                "reply": resp.content.strip(),
                "reasoning_len": len(resp.reasoning or ""),
            }
        except Exception as exc:
            elapsed = time.time() - start_t
            return {
                "model": model_name,
                "status": "error",
                "elapsed_s": round(elapsed, 2),
                "error": str(exc),
            }

    def get_openai_client(self) -> Any:
        """Return an openai.OpenAI client preconfigured for RCP if openai is installed."""
        try:
            import openai

            return openai.OpenAI(base_url=self.base_url, api_key=self.api_key)
        except ImportError as exc:
            raise ImportError(
                "openai package is not installed. RCPClient provides native, zero-dependency "
                "HTTP calls without needing openai. If you want to use the OpenAI SDK, install "
                "openai via pip."
            ) from exc


class RCPChat:
    """Stateful multi-turn chat harness for RCP models."""

    def __init__(
        self,
        client: RCPClient,
        system: Optional[str] = None,
        model: Optional[str] = None,
        reasoning: Optional[bool] = None,
        reasoning_effort: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        self.client = client
        self.system = system
        self.model = normalize_model_name(model or client.default_model)
        self.reasoning = client.default_reasoning if reasoning is None else reasoning
        self.reasoning_effort = (
            client.default_reasoning_effort
            if reasoning_effort is None
            else reasoning_effort
        )
        self.temperature = (
            client.default_temperature if temperature is None else temperature
        )
        self.max_tokens = max_tokens

        self._messages: List[Dict[str, Any]] = []
        if self.system:
            self._messages.append({"role": "system", "content": self.system})

    @property
    def history(self) -> List[Dict[str, Any]]:
        """Return a copy of the conversation messages."""
        return [dict(m) for m in self._messages]

    def add_message(
        self, role: str, content: str, reasoning_content: Optional[str] = None
    ) -> None:
        """Manually append a message to history."""
        msg: Dict[str, Any] = {"role": role, "content": content}
        if reasoning_content:
            msg["reasoning_content"] = reasoning_content
        self._messages.append(msg)

    def send(
        self,
        prompt: str,
        reasoning: Optional[bool] = None,
        reasoning_effort: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> RCPResponse:
        """Send a user turn and record the assistant response in conversation history."""
        self._messages.append({"role": "user", "content": prompt})

        effective_reasoning = self.reasoning if reasoning is None else reasoning
        effective_effort = (
            self.reasoning_effort if reasoning_effort is None else reasoning_effort
        )
        effective_temp = self.temperature if temperature is None else temperature
        effective_max = self.max_tokens if max_tokens is None else max_tokens

        try:
            resp = self.client.create_chat_completion(
                messages=self._messages,
                model=self.model,
                reasoning=effective_reasoning,
                reasoning_effort=effective_effort,
                temperature=effective_temp,
                max_tokens=effective_max,
                timeout=timeout,
                **kwargs,
            )
        except Exception:
            # Roll back user message on failure so session remains clean
            self._messages.pop()
            raise

        # Record assistant reply in history
        self._messages.append(resp.to_dict())
        return resp

    def reset(self) -> None:
        """Clear conversation history, preserving the initial system prompt."""
        self._messages.clear()
        if self.system:
            self._messages.append({"role": "system", "content": self.system})

    def undo(self) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """Undo the last (user, assistant) turn if present."""
        if len(self._messages) >= 2 and self._messages[-1].get("role") == "assistant":
            assistant_turn = self._messages.pop()
            user_turn = self._messages.pop()
            return user_turn, assistant_turn
        return None

    def fork(self) -> RCPChat:
        """Create an independent copy of this chat session with identical history."""
        clone = RCPChat(
            client=self.client,
            system=self.system,
            model=self.model,
            reasoning=self.reasoning,
            reasoning_effort=self.reasoning_effort,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        clone._messages = [dict(m) for m in self._messages]
        return clone
