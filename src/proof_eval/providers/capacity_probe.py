"""Exercise independent full-context streams without starting task budgets."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

from proof_eval.evidence.io import write_json

from .lemex_local import MODEL


def metrics(endpoint: str) -> dict[str, float]:
    with urlopen(endpoint.removesuffix("/v1") + "/metrics", timeout=15) as response:
        raw = response.read().decode()
    names = {
        "vllm:num_requests_running",
        "vllm:num_requests_waiting",
        "vllm:num_preemptions_total",
        "vllm:kv_cache_usage_perc",
        "vllm:generation_tokens_total",
    }
    values = {}
    for line in raw.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        name = parts[0].split("{")[0]
        if name in names:
            values[name] = values.get(name, 0.0) + float(parts[1])
    return values


def exercise_full_context(
    endpoint: str,
    tokenizer_path: Path,
    folder: Path,
    workers: int,
    *,
    context_tokens: int = 266400,
    output_tokens: int = 16384,
) -> dict:
    """Require simultaneous decoding, full usage and no KV preemption.

    Stress sampling belongs exclusively to this synthetic admission check.
    Production native sampling and task prompts are never changed.
    """
    from transformers import AutoTokenizer

    if not 1 <= workers <= 128 or output_tokens >= context_tokens:
        raise ValueError("Invalid full-context capacity probe")
    folder.mkdir(parents=True, exist_ok=False)
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, local_files_only=True)
    input_tokens = context_tokens - output_tokens
    filler = tokenizer.encode(
        "This paragraph is neutral background text for a context capacity check.\n",
        add_special_tokens=False,
    )
    body = (filler * (input_tokens // len(filler) + 1))[:input_tokens]
    needle = "The unique verification code is Silver-6832-Cedar."
    ids = tokenizer.encode(needle, add_special_tokens=False)
    middle = input_tokens * 3 // 4
    retrieval_body = body[:middle] + ids + body[middle + len(ids) :]
    rendered = tokenizer.apply_chat_template(
        [
            {
                "role": "user",
                "content": tokenizer.decode(retrieval_body)
                + "\nReturn only the unique verification code from this document.",
            }
        ],
        tokenize=True,
        return_dict=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    if hasattr(rendered, "input_ids"):
        rendered = rendered.input_ids
    if rendered and isinstance(rendered[0], list):
        rendered = rendered[0]
    payload = {
        "model": MODEL,
        "prompt": rendered,
        "max_tokens": 128,
        "temperature": 0,
        "stream": False,
    }
    with urlopen(
        Request(
            endpoint + "/completions",
            json.dumps(payload).encode(),
            {"Content-Type": "application/json"},
        ),
        timeout=1200,
    ) as response:
        retrieval = json.load(response)
    answer = retrieval["choices"][0]["text"]
    write_json(
        folder / "retrieval.json",
        {
            "input_tokens": len(rendered),
            "answer": answer,
            "usage": retrieval.get("usage"),
        },
    )
    if "Silver-6832-Cedar" not in answer:
        raise RuntimeError("Long-context retrieval did not return the expected code")
    before = metrics(endpoint)
    barrier = threading.Barrier(workers)
    stop = threading.Event()
    samples = []

    def monitor() -> None:
        with (folder / "metrics.jsonl").open("a") as stream:
            while not stop.wait(2):
                try:
                    sample = {"epoch": time.time(), **metrics(endpoint)}
                    samples.append(sample)
                    stream.write(json.dumps(sample) + "\n")
                    stream.flush()
                    write_json(
                        folder / "progress.json",
                        {"stage": "full_context_streams", **sample},
                    )
                except OSError:
                    continue

    def request(index: int) -> dict:
        prefix = tokenizer.encode(
            f"Independent capacity request {index}: ", add_special_tokens=False
        )
        prompt = prefix + body[len(prefix) :]
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "max_tokens": output_tokens,
            "ignore_eos": True,
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 20,
            "seed": 100 + index,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        raw_payload = json.dumps(payload).encode()
        barrier.wait(timeout=60)
        started, first, usage, output_hash = time.time(), None, None, hashlib.sha256()
        with urlopen(
            Request(
                endpoint + "/completions",
                raw_payload,
                {"Content-Type": "application/json"},
            ),
            timeout=2400,
        ) as response:
            for line in response:
                if not line.startswith(b"data: ") or line.strip() == b"data: [DONE]":
                    continue
                event = json.loads(line[6:])
                if "error" in event:
                    raise RuntimeError(str(event["error"]))
                for choice in event.get("choices", []):
                    text = choice.get("text", "")
                    if text:
                        first = first or time.time()
                        output_hash.update(text.encode())
                usage = event.get("usage") or usage
        result = {
            "index": index,
            "started_epoch": started,
            "first_token_epoch": first,
            "finished_epoch": time.time(),
            "usage": usage,
            "request_sha256": hashlib.sha256(raw_payload).hexdigest(),
            "output_sha256": output_hash.hexdigest(),
        }
        write_json(folder / f"request-{index}.json", result)
        if (
            not first
            or not usage
            or usage.get("prompt_tokens") != input_tokens
            or usage.get("completion_tokens") != output_tokens
        ):
            raise RuntimeError("A full-context stream returned incomplete usage")
        return result

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(request, range(workers)))
    finally:
        stop.set()
        thread.join(timeout=20)
    after = metrics(endpoint)
    overlap = max(r["first_token_epoch"] for r in rows) < min(
        r["finished_epoch"] for r in rows
    )
    preemptions = after.get("vllm:num_preemptions_total", 0) - before.get(
        "vllm:num_preemptions_total", 0
    )
    peak = max((s.get("vllm:num_requests_running", 0) for s in samples), default=0)
    if not overlap or preemptions or peak < workers:
        raise RuntimeError(
            f"Full-window admission failed: overlap={overlap}, preemptions={preemptions}, peak={peak}"
        )
    elapsed = max(r["finished_epoch"] for r in rows) - min(
        r["started_epoch"] for r in rows
    )
    receipt = {
        "status": "pressure_passed",
        "workers": workers,
        "context_tokens": context_tokens,
        "input_tokens_each": input_tokens,
        "output_tokens_each": output_tokens,
        "all_decode_overlap": overlap,
        "preemptions": preemptions,
        "peak_running": peak,
        "elapsed_seconds": elapsed,
        "aggregate_decode_tokens_per_second": workers * output_tokens / elapsed,
        "rows": rows,
    }
    write_json(folder / "pressure-receipt.json", receipt)
    return receipt
