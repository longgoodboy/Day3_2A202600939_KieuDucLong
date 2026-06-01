import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.agent.agent import ReActAgent
from src.agent.agent_v2 import ReActAgentV2
from src.chatbot import Chatbot
from src.core.provider_factory import ProviderConfigError, create_provider
from src.telemetry.logger import logger
from src.tools.registry import get_tool_registry

from evaluation.validators import summarize_events, validate_case


DEFAULT_RESULTS_PATH = ROOT_DIR / "evaluation" / "results" / "benchmark_results.csv"
DEFAULT_TEST_CASES_PATH = ROOT_DIR / "evaluation" / "test_cases.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic Lab 3 business benchmark.")
    parser.add_argument("--provider", default="mimo", help="Provider to benchmark, e.g. mimo, gemini, openai.")
    parser.add_argument(
        "--mode",
        choices=["chatbot", "agent-v1", "agent-v2", "all"],
        default="all",
        help="Runner mode to benchmark.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional number of test cases to run.")
    parser.add_argument("--case-id", default=None, help="Optional single case id, e.g. B11.")
    parser.add_argument("--case-ids", default=None, help="Optional comma-separated case ids, e.g. B02,B03,B05.")
    parser.add_argument("--output", default=str(DEFAULT_RESULTS_PATH), help="CSV output path.")
    parser.add_argument("--test-cases", default=str(DEFAULT_TEST_CASES_PATH), help="JSON test cases path.")
    parser.add_argument(
        "--request-delay",
        type=float,
        default=0.0,
        help="Minimum seconds to wait between provider.generate calls.",
    )
    parser.add_argument(
        "--agent-max-retries",
        type=int,
        default=2,
        help="Max retries for agent-v2 during benchmark.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing CSV instead of overwriting.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    test_cases = load_test_cases(Path(args.test_cases), args.case_id, args.case_ids, args.limit)
    modes = ["chatbot", "agent-v1", "agent-v2"] if args.mode == "all" else [args.mode]

    rows = []
    for mode in modes:
        try:
            provider = create_provider(args.provider)
        except ProviderConfigError as exc:
            rows.extend(skipped_rows(test_cases, mode, args.provider, str(exc)))
            continue
        if args.request_delay > 0:
            provider = ThrottledProvider(provider, args.request_delay)

        for test_case in test_cases:
            rows.append(run_case(provider, mode, args.provider, test_case, args.agent_max_retries))

    output_path = Path(args.output)
    write_rows(output_path, rows, append=args.append)
    print(f"Wrote {len(rows)} benchmark rows to {output_path}")
    return 0


def load_test_cases(
    path: Path,
    case_id: str | None,
    case_ids: str | None,
    limit: int | None,
) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        test_cases = json.load(file)

    if case_id:
        test_cases = [case for case in test_cases if case["id"] == case_id]
    if case_ids:
        wanted = [item.strip() for item in case_ids.split(",") if item.strip()]
        wanted_set = set(wanted)
        by_id = {case["id"]: case for case in test_cases}
        test_cases = [by_id[case_id] for case_id in wanted if case_id in wanted_set and case_id in by_id]
    if limit is not None:
        test_cases = test_cases[:limit]
    return test_cases


def skipped_rows(
    test_cases: List[Dict[str, Any]],
    mode: str,
    provider_name: str,
    reason: str,
) -> List[Dict[str, Any]]:
    return [
        {
            "case_id": test_case["id"],
            "category": test_case["category"],
            "mode": mode,
            "provider": provider_name,
            "status": "skipped",
            "passed": False,
            "reason": f"Skipped benchmark: {reason}",
            "answer": "",
            "llm_calls": 0,
            "tool_calls": 0,
            "tool_sequence": "",
            "total_tokens": 0,
            "total_latency_ms": 0,
            "wall_time_ms": 0,
            "parser_errors": 0,
            "retries": 0,
            "provider_errors": 0,
            "termination_reason": "skipped",
        }
        for test_case in test_cases
    ]


def run_case(
    provider: Any,
    mode: str,
    provider_name: str,
    test_case: Dict[str, Any],
    agent_max_retries: int,
) -> Dict[str, Any]:
    captured_events: List[Dict[str, Any]] = []
    original_log_event = logger.log_event

    def capture_log_event(event: str, data: Dict[str, Any]) -> None:
        captured_events.append({"event": event, "data": data})
        original_log_event(event, data)

    logger.log_event = capture_log_event
    started = time.perf_counter()
    status = "completed"
    answer = ""
    error_reason = ""

    try:
        runner = create_runner(mode, provider, agent_max_retries)
        answer = runner.run(test_case["query"])
    except Exception as exc:
        status = "runtime_error"
        error_reason = f"{type(exc).__name__}: {exc}"
    finally:
        wall_time_ms = int((time.perf_counter() - started) * 1000)
        logger.log_event = original_log_event

    metrics = summarize_events(captured_events)
    if status == "completed":
        validation_case = dict(test_case)
        if mode == "chatbot":
            validation_case["required_tools"] = []
            validation_case["forbidden_tools"] = []
        validation = validate_case(answer, captured_events, validation_case)
        passed = bool(validation["passed"])
        reason = validation["reason"]
    else:
        passed = False
        reason = error_reason

    return {
        "case_id": test_case["id"],
        "category": test_case["category"],
        "mode": mode,
        "provider": provider_name,
        "status": status,
        "passed": passed,
        "reason": reason,
        "answer": one_line(answer),
        "llm_calls": metrics["llm_calls"],
        "tool_calls": metrics["tool_calls"],
        "tool_sequence": metrics["tool_sequence"],
        "total_tokens": metrics["total_tokens"],
        "total_latency_ms": metrics["total_latency_ms"],
        "wall_time_ms": wall_time_ms,
        "parser_errors": metrics["parser_errors"],
        "retries": metrics["retries"],
        "provider_errors": metrics["provider_errors"],
        "termination_reason": metrics["termination_reason"],
    }


def create_runner(mode: str, provider: Any, agent_max_retries: int) -> Any:
    if mode == "chatbot":
        return Chatbot(provider)
    if mode == "agent-v1":
        return ReActAgent(provider, get_tool_registry())
    if mode == "agent-v2":
        return ReActAgentV2(provider, get_tool_registry(), max_retries=agent_max_retries)
    raise ValueError(f"Unknown mode: {mode}")


class ThrottledProvider:
    """Wrap an LLM provider and enforce a delay between generate calls."""

    def __init__(self, provider: Any, request_delay: float):
        self.provider = provider
        self.request_delay = request_delay
        self.last_call = 0.0
        self.model_name = provider.model_name
        self.api_key = getattr(provider, "api_key", None)
        self.provider_name = getattr(provider, "provider_name", None)

    def generate(self, prompt: str, system_prompt: str | None = None) -> Dict[str, Any]:
        elapsed = time.perf_counter() - self.last_call
        if self.last_call and elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        try:
            return self.provider.generate(prompt, system_prompt=system_prompt)
        finally:
            self.last_call = time.perf_counter()

    def stream(self, prompt: str, system_prompt: str | None = None):
        return self.provider.stream(prompt, system_prompt=system_prompt)


def write_rows(path: Path, rows: List[Dict[str, Any]], append: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id",
        "category",
        "mode",
        "provider",
        "status",
        "passed",
        "reason",
        "answer",
        "llm_calls",
        "tool_calls",
        "tool_sequence",
        "total_tokens",
        "total_latency_ms",
        "wall_time_ms",
        "parser_errors",
        "retries",
        "provider_errors",
        "termination_reason",
    ]
    mode = "a" if append and path.exists() else "w"
    with path.open(mode, newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if mode == "w":
            writer.writeheader()
        writer.writerows(rows)


def one_line(value: str) -> str:
    return " ".join(str(value).split())


if __name__ == "__main__":
    raise SystemExit(main())
