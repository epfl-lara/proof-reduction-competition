"""Two isolated, non-retried reasoning-cap probes; never save reasoning text."""
from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from proof_eval.rcp import RCPClient, map_rcp_reasoning

OUT = Path(__file__).resolve().parent
MODEL = "deepseek-ai/DeepSeek-V4.1-Flash"
PROMPT = "Compute the remainder of 7^123 when divided by 1009. Return only the integer as your final answer."
BUDGETS = (32, 128)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def write(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temporary.replace(path)


def read(path):
    return json.loads(path.read_text())


def reasoning_tokens(usage):
    details = usage.get("completion_tokens_details")
    value = details.get("reasoning_tokens") if isinstance(details, dict) else None
    return value if type(value) is int and value >= 0 else None


def classify(record):
    if record["status"] != "received":
        return record["status"]
    count, budget = record["reasoning_tokens"], record["thinking_token_budget"]
    if count is None:
        return "inconclusive_missing_provider_reasoning_count"
    if count == budget and record["content"].strip():
        return "boundary_and_final_content_support_enforcement"
    if count < budget:
        return "inconclusive_completion_before_requested_boundary"
    if count > budget:
        return "provider_reasoning_count_exceeds_requested_budget"
    return "inconclusive_boundary_without_final_content"


def summarize(config, records, status):
    started = sum((OUT / f"budget_{budget}" / "started.json").exists() for budget in BUDGETS)
    received = [r for r in records if r["status"] == "received"]
    both_boundaries = len(received) == 2 and all(r["interpretation"] == "boundary_and_final_content_support_enforcement" for r in received)
    exceed = [r["thinking_token_budget"] for r in received if r["interpretation"] == "provider_reasoning_count_exceeds_requested_budget"]
    if both_boundaries:
        conclusion = "Both provider-reported reasoning counts equal their requested boundary and have nonempty final content. This supports enforcement for this model on the tested RCP route; it does not establish behavior for other models, workloads, or deployments."
    elif any(r["status"] == "explicit_field_rejection" for r in records):
        conclusion = "The tested route explicitly rejected the thinking_token_budget field; no second request was made."
    elif exceed:
        conclusion = "Provider-reported reasoning exceeded the requested thinking budget in the recorded probes. The request did not establish an effective cap on this route. Proxy forwarding and backend handling remain unverified; field acceptance alone is not enforcement."
    else:
        conclusion = "Inconclusive for enforcement: request success, shorter output, or natural completion before the boundary does not demonstrate forced reasoning termination."
    summary = {"schema_version": 1, "status": status, "updated_at": now(), "config": config,
        "generation_requests_started": started, "maximum_aggregate_generation_allowance": 1024,
        "started_request_generation_allowance": started * 512, "requests": records,
        "total_reported_completion_tokens": sum(r["usage"].get("completion_tokens", 0) for r in received),
        "total_reported_reasoning_tokens": sum(r["reasoning_tokens"] for r in received) if all(r["reasoning_tokens"] is not None for r in received) else None,
        "conclusion": conclusion, "reasoning_text_saved": False, "credentials_or_endpoint_saved": False,
        "limitations": ["One stochastic draw per requested thinking budget.",
            "Only this exact model and configured RCP route were exercised.",
            "No server trace, backend version, tokenizer token IDs, or forced-boundary event was available.",
            "Arithmetic correctness and final-answer delivery are distinct from cap enforcement.",
            "The frozen benchmark requests and runtime source were not changed."]}
    write(OUT / "probe.json", summary)
    return summary


def main():
    client_sha = sha_bytes((ROOT / "src/proof_eval/rcp.py").read_bytes())
    config = {"model": MODEL, "prompt": PROMPT, "thinking_token_budgets": list(BUDGETS),
        "temperature": 0.3, "reasoning": True, "reasoning_effort": "high", "max_tokens": 512,
        "timeout_seconds": 180, "maximum_generation_requests": 2, "automatic_retries": 0,
        "expected_answer": str(pow(7, 123, 1009)), "client_sha256": client_sha,
        "script_sha256": sha_bytes(Path(__file__).read_bytes()),
        "client_method": "RCPClient.create_chat_completion", "budget_field_location": "top-level keyword argument and serialized request field"}
    with (OUT / ".probe.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config_path = OUT / "config.json"
        if config_path.exists() and read(config_path) != config:
            raise ValueError("Probe configuration changed; refusing to resample")
        write(config_path, config)
        client = RCPClient(env_path=ROOT / ".env", timeout=180)
        records = []
        summarize(config, records, "running")
        for budget in BUDGETS:
            folder = OUT / f"budget_{budget}"
            folder.mkdir(exist_ok=True)
            arguments = {"messages": [{"role": "user", "content": PROMPT}], "model": MODEL,
                "temperature": 0.3, "reasoning": True, "reasoning_effort": "high",
                "max_tokens": 512, "timeout": 180, "thinking_token_budget": budget}
            args_path = folder / "call_args.json"
            if args_path.exists() and read(args_path) != arguments:
                raise ValueError("Saved call arguments changed")
            write(args_path, arguments)
            chat_kwargs, auto_extra = map_rcp_reasoning(MODEL, True, "high")
            write(folder / "expected_wire_payload.json", {"model": MODEL, "messages": arguments["messages"],
                "chat_template_kwargs": chat_kwargs, "extra_body": auto_extra, "temperature": 0.3,
                "max_tokens": 512, "thinking_token_budget": budget})
            result_path = folder / "result.json"
            if result_path.exists():
                result = read(result_path)
            elif records and records[0]["status"] == "explicit_field_rejection":
                result = {"status": "skipped_after_explicit_field_rejection", "thinking_token_budget": budget,
                          "reason": "First route request explicitly rejected thinking_token_budget; second call prohibited by probe protocol."}
                write(result_path, result)
            elif (folder / "started.json").exists():
                result = {"status": "indeterminate_after_interruption", "thinking_token_budget": budget,
                          "reason": "Durable start marker exists without a saved response; never resample."}
                write(result_path, result)
            else:
                write(folder / "started.json", {"started_at": now(), "client_sha256": client_sha,
                    "call_args_sha256": sha_bytes(json.dumps(arguments, sort_keys=True).encode())})
                started = time.monotonic()
                print(json.dumps({"event": "request_started", "thinking_token_budget": budget}), flush=True)
                try:
                    response = client.create_chat_completion(**arguments)
                    usage = response.usage
                    result = {"status": "received", "thinking_token_budget": budget,
                        "content": response.content, "returned_model": response.model, "usage": usage,
                        "finish_reason": response.finish_reason,
                        "reasoning_tokens": reasoning_tokens(usage),
                        "reasoning_characters": len(response.reasoning_content or ""),
                        "elapsed_seconds": round(time.monotonic() - started, 3),
                        "answer_correct": response.content.strip() == config["expected_answer"]}
                except Exception as exc:
                    error = str(exc).replace(client.api_key, "[REDACTED]").replace(client.base_url, "[RCP_ENDPOINT]")
                    error = re.sub(r"https?://[^\s\"']+", "[URL]", error)[:4000]
                    rejected = "thinking_token_budget" in error and bool(re.search(
                        r"unsupported|unknown|unrecognized|not (?:supported|allowed|permitted)|extra.inputs|unexpected|invalid.parameter|invalid.request", error, re.I))
                    result = {"status": "explicit_field_rejection" if rejected else "request_error",
                        "thinking_token_budget": budget, "error_type": type(exc).__name__, "error": error,
                        "http_status": getattr(exc.__cause__, "code", None),
                        "elapsed_seconds": round(time.monotonic() - started, 3)}
                result["interpretation"] = classify(result)
                write(result_path, result)
            records.append(result)
            summarize(config, records, "complete" if len(records) == len(BUDGETS) else "running")
            print(json.dumps({"event": "request_recorded", "thinking_token_budget": budget,
                "status": result["status"], "reasoning_tokens": result.get("reasoning_tokens"),
                "completion_tokens": result.get("usage", {}).get("completion_tokens"),
                "final_characters": len(result.get("content", "")), "finish_reason": result.get("finish_reason")}), flush=True)


if __name__ == "__main__":
    main()
