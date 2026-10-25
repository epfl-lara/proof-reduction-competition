"""A training-only ReAct transport to the unchanged Arena tool dispatcher."""

from __future__ import annotations

import json

ALLOWED_OPS = frozenset(
    {
        "check",
        "status",
        "profile",
        "goals",
        "search",
        "read",
        "outline",
        "semantic_search",
        "web_search",
        "web_open",
        "finish",
    }
)

ACTION_INSTRUCTIONS = """
Training transport: interact with the same host-owned Arena proof/source tools
by ending each response with exactly one <arena_action>JSON object</arena_action>.
Reason before the action if useful. The host returns the real tool observation.
Actions are the tool RPC objects, not shell commands:
  {"op":"check","code":"COMPLETE replacement Lean declaration"}
  {"op":"goals","code":"COMPLETE replacement declaration"}
  {"op":"profile","code":"COMPLETE declaration","version":"VERSION"}
  {"op":"status"}
  {"op":"search","query":"literal symbol/property","limit":30}
  {"op":"outline","path":"relative/File.lean"}
  {"op":"read","path":"relative/File.lean","start":1,"end":180}
  {"op":"semantic_search","query":"concept","limit":10}
  {"op":"web_search","query":"documentation query","limit":5}
  {"op":"web_open","url":"https://primary/source"}
  {"op":"finish","reason":"short factual reason"}
Source/version restrictions, original token/heartbeat denominators and the
all-version checker are unchanged. Only the host can update the best proof.
Do not claim a score or write a verdict yourself. Invalid proposals never replace
the incumbent. The reward is (final best verified Arena score - original score)
/ 100. Score feedback is useful partial credit; tool count/length gets no bonus.
No deterministic cleanup or cross-rollout restart notes are supplied.
Finish with the finish action when further useful improvement seems unlikely.
""".strip()


def parse_action(text: str) -> dict:
    # Qwen may quote action examples in its reasoning. Dispatch only its final
    # answer; the caller still saves the original text, tokens and logprobs.
    answer = text.lstrip()
    if answer.startswith("<think>"):
        _, closed, answer = answer[len("<think>") :].partition("</think>")
        if not closed:
            raise ValueError("A tool action requires a completed final answer")
    opening = "<arena_action>"
    start = answer.find(opening)
    if start < 0:
        raise ValueError("Return exactly one <arena_action>JSON object</arena_action>")
    payload = answer[start + len(opening) :].lstrip()
    # Decode JSON before looking for the closing envelope: a Lean string may
    # itself contain literal tags, which are data rather than another action.
    value, end = json.JSONDecoder().raw_decode(payload)
    if payload[end:].strip() != "</arena_action>":
        raise ValueError("Return exactly one <arena_action>JSON object</arena_action>")
    if not isinstance(value, dict) or value.get("op") not in ALLOWED_OPS:
        raise ValueError("Unsupported Arena action")
    return value


def initial_messages(
    pack: dict, system_prompt: str, episode_seconds: int
) -> list[dict]:
    user = {
        "task": pack["row"],
        "source_context": pack["source_context"],
        "required_versions": [
            v for entry in pack["row"]["version_info"] for v in entry
        ],
        "original_score": pack["incumbent"]["scores"]["combined_pct"],
        "budget_seconds": episode_seconds,
    }
    return [
        {"role": "system", "content": system_prompt + "\n\n" + ACTION_INSTRUCTIONS},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]
