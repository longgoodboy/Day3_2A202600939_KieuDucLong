import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT_DIR / "evaluation" / "results" / "benchmark_results.csv"
DEFAULT_OUTPUT = ROOT_DIR / "evaluation" / "results" / "summary.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze deterministic benchmark CSV.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Benchmark CSV path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Markdown summary output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_rows(Path(args.input))
    summary = render_summary(rows)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary, encoding="utf-8")
    print(f"Wrote benchmark summary to {output_path}")
    return 0


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def render_summary(rows: List[Dict[str, str]]) -> str:
    if not rows:
        return "# Benchmark Summary\n\nNo benchmark rows found.\n"

    groups: Dict[tuple[str, str], List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["mode"], row["provider"])].append(row)

    lines = [
        "# Benchmark Summary",
        "",
        "Deterministic validators were used. No LLM-as-a-judge scoring was used.",
        "",
        "## Overall Results",
        "",
        "| Mode | Provider | Cases | Skipped | Evaluated | Passed | Success Rate | Avg Tokens | Avg Latency ms | Parser Errors | Retries | Provider Errors |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for (mode, provider), group_rows in sorted(groups.items()):
        total = len(group_rows)
        skipped = sum(1 for row in group_rows if row.get("status") == "skipped")
        evaluated_rows = [row for row in group_rows if row.get("status") != "skipped"]
        evaluated = len(evaluated_rows)
        passed = sum(1 for row in evaluated_rows if as_bool(row.get("passed")))
        success_rate = passed / evaluated if evaluated else 0
        avg_tokens = average_int(evaluated_rows, "total_tokens")
        avg_latency = average_int(evaluated_rows, "total_latency_ms")
        parser_errors = sum_int(group_rows, "parser_errors")
        retries = sum_int(group_rows, "retries")
        provider_errors = sum_int(group_rows, "provider_errors")
        lines.append(
            f"| {mode} | {provider} | {total} | {skipped} | {evaluated} | {passed} | {success_rate:.1%} | "
            f"{avg_tokens:.0f} | {avg_latency:.0f} | {parser_errors} | {retries} | {provider_errors} |"
        )

    lines.extend(
        [
            "",
            "## Case Details",
            "",
            "| Case | Category | Mode | Provider | Passed | Reason | Tool Sequence |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        reason = escape_cell(row.get("reason", ""))
        tools = escape_cell(row.get("tool_sequence", ""))
        lines.append(
            f"| {row.get('case_id', '')} | {row.get('category', '')} | {row.get('mode', '')} | "
            f"{row.get('provider', '')} | {row.get('passed', '')} | {reason} | {tools} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Business benchmark cases are separate from reliability tests.",
            "- Reliability behaviors such as malformed JSON, markdown-fenced JSON, provider exception, and repeated action are covered by mock tests.",
            "- MiMo Token Plan monetary cost is not estimated; token usage is still tracked.",
        ]
    )
    return "\n".join(lines) + "\n"


def average_int(rows: List[Dict[str, str]], field: str) -> float:
    if not rows:
        return 0.0
    return sum_int(rows, field) / len(rows)


def sum_int(rows: List[Dict[str, str]], field: str) -> int:
    total = 0
    for row in rows:
        try:
            total += int(float(row.get(field, 0) or 0))
        except ValueError:
            continue
    return total


def as_bool(value: Any) -> bool:
    return str(value).lower() == "true"


def escape_cell(value: str) -> str:
    return str(value).replace("|", "\\|")


if __name__ == "__main__":
    raise SystemExit(main())
