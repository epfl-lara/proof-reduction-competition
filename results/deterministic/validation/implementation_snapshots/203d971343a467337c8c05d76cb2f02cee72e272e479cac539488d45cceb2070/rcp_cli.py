"""Interactive RCP provider CLI; paid requests are explicit."""

import json
import sys

from .rcp import (
    DEFAULT_MODEL,
    DEFAULT_REASONING,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_TEMPERATURE,
    RCPClient,
    normalize_model_name,
)


def main() -> None:
    """CLI entrypoint for testing and interacting with RCP models."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Call models from EPFL RCP inference cluster."
    )
    parser.add_argument(
        "--test", action="store_true", help="Test connectivity to the 4 target models."
    )
    parser.add_argument(
        "--list-models", action="store_true", help="List all available models on RCP."
    )
    parser.add_argument(
        "--model", type=str, default=DEFAULT_MODEL, help="Model to use (or alias)."
    )
    parser.add_argument("--prompt", type=str, help="Single prompt to execute.")
    parser.add_argument(
        "--system",
        type=str,
        default="You are a helpful assistant.",
        help="System prompt.",
    )
    parser.add_argument(
        "--chat", action="store_true", help="Launch interactive multi-turn chat."
    )
    parser.add_argument(
        "--reasoning",
        action="store_true",
        default=DEFAULT_REASONING,
        help=f"Enable thinking mode (default: {DEFAULT_REASONING}).",
    )
    parser.add_argument(
        "--no-reasoning",
        action="store_false",
        dest="reasoning",
        help="Disable thinking mode.",
    )
    parser.add_argument(
        "--effort",
        type=str,
        default=DEFAULT_REASONING_EFFORT,
        help=f"Reasoning effort: low, medium, high, xhigh (default: {DEFAULT_REASONING_EFFORT}).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help=f"Sampling temperature (default: {DEFAULT_TEMPERATURE}).",
    )
    parser.add_argument(
        "--timeout", type=float, default=45.0, help="Timeout in seconds."
    )
    args = parser.parse_args()

    try:
        client = RCPClient(
            default_temperature=args.temperature,
            default_reasoning=args.reasoning,
            default_reasoning_effort=args.effort,
            timeout=args.timeout,
        )
    except Exception as exc:
        print(f"Error initializing RCP client: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.list_models:
        print(f"Querying models from {client.base_url}...")
        models = client.list_models()
        print(f"Total available models ({len(models)}):")
        for m in models:
            print(f"  - {m}")
        return

    if args.test:
        target_models = [
            "deepseek-ai/DeepSeek-V4.1-Flash",
            "Qwen/Qwen3.5-397B-A17B",
            "Qwen/Qwen3.6-35B-A3B",
            "Qwen/Qwen3.8-27B",
        ]
        print(f"Testing 4 models on RCP ({client.base_url}):")
        for m in target_models:
            print(f"\nTesting {m} (timeout={args.timeout}s)...", flush=True)
            res = client.test_model(m, timeout=args.timeout)
            if res["status"] == "ok":
                print(f"  ✅ SUCCESS: {res['elapsed_s']}s | reply: {res['reply']!r}")
            else:
                print(f"  ❌ FAILED ({res['elapsed_s']}s): {res['error']}")
        return

    if args.prompt:
        model = normalize_model_name(args.model)
        print(
            f"Calling {model} (reasoning={args.reasoning}, effort={args.effort}, temp={args.temperature})...",
            flush=True,
        )
        resp = client.complete(
            prompt=args.prompt,
            system=args.system,
            model=model,
            reasoning=args.reasoning,
            reasoning_effort=args.effort,
            temperature=args.temperature,
            timeout=args.timeout,
        )
        if resp.reasoning:
            print(f"\n[Reasoning Trace]\n{resp.reasoning.strip()}\n")
        print(f"[Response]\n{resp.content.strip()}")
        return

    if args.chat:
        model = normalize_model_name(args.model)
        print(f"Starting chat harness with {model}")
        print(
            f"Reasoning: {args.reasoning} (effort: {args.effort}, temp: {args.temperature})"
        )
        print(
            "Type 'exit' or 'quit' to quit, 'reset' to clear history, 'history' to view.\n"
        )

        chat = client.chat_harness(
            system=args.system,
            model=model,
            reasoning=args.reasoning,
            reasoning_effort=args.effort,
            temperature=args.temperature,
        )

        while True:
            try:
                user_input = input("User > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit"}:
                print("Goodbye!")
                break
            if user_input.lower() == "reset":
                chat.reset()
                print("Conversation history reset.")
                continue
            if user_input.lower() == "history":
                print(json.dumps(chat.history, indent=2))
                continue

            try:
                resp = chat.send(user_input, timeout=args.timeout)
                if resp.reasoning:
                    print(f"\n🤔 [Thinking: {len(resp.reasoning)} chars]")
                print(f"\nAssistant > {resp.content}\n")
            except Exception as exc:
                print(f"\n❌ Error: {exc}\n")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
