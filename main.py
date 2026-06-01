import argparse
import sys
from typing import Any

from src.agent.agent import ReActAgent
from src.agent.agent_v2 import ReActAgentV2
from src.chatbot import Chatbot
from src.core.provider_factory import ProviderConfigError, create_provider
from src.tools.registry import get_tool_registry


DEMO_PROMPT = "What products do you sell?"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lab 3: Chatbot vs ReAct Agent")
    parser.add_argument(
        "--mode",
        choices=["chatbot", "agent-v1", "agent-v2"],
        default="chatbot",
        help="Application mode to run.",
    )
    parser.add_argument(
        "--provider",
        choices=["mimo", "gemini", "google", "openai", "local"],
        default=None,
        help="Optional provider override. Defaults to DEFAULT_PROVIDER or mimo.",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="Prompt to run once. If omitted in non-interactive mode, a demo prompt is used.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run an interactive CLI loop.",
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    try:
        llm = create_provider(args.provider)
    except ProviderConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if args.mode == "chatbot":
        runner = Chatbot(llm)
    elif args.mode == "agent-v1":
        runner = ReActAgent(llm, get_tool_registry())
    elif args.mode == "agent-v2":
        runner = ReActAgentV2(llm, get_tool_registry())
    else:
        print(f"Mode '{args.mode}' is not implemented yet. Complete later phases first.", file=sys.stderr)
        return 1

    if args.interactive:
        return run_interactive(runner)

    prompt = args.prompt or DEMO_PROMPT
    print(runner.run(prompt))
    return 0


def run_interactive(runner: Any) -> int:
    print("Interactive mode. Type 'exit' or 'quit' to stop.")
    while True:
        try:
            user_input = input("User: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if user_input.lower() in {"exit", "quit"}:
            return 0
        if not user_input:
            continue

        print(f"Assistant: {runner.run(user_input)}")


if __name__ == "__main__":
    raise SystemExit(main())
