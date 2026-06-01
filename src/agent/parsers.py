import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional


class ActionParseError(ValueError):
    """Raised when an LLM output cannot be parsed into one safe action."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ParsedAction:
    """A parsed tool action."""

    tool_name: str
    arguments: Dict[str, Any]
    raw: str


def parse_final_answer(content: str) -> Optional[str]:
    """Extract a Final Answer if the model used the required marker."""
    match = re.search(r"Final Answer:\s*(.*)", content, flags=re.DOTALL)
    if match is None:
        return None
    answer = match.group(1).strip()
    return answer or None


def parse_single_action(content: str) -> ParsedAction:
    """
    Parse exactly one action from ReAct text, raw JSON, or fenced JSON.

    Supported formats:
    - Action: tool_name({"arg": "value"})
    - {"tool_name": "tool_name", "arguments": {"arg": "value"}}
    - ```json
      {"tool": "tool_name", "args": {"arg": "value"}}
      ```
    """
    if "Observation:" in content:
        raise ActionParseError(
            "MODEL_WRITTEN_OBSERVATION",
            "Model output contained Observation. The runtime must write observations.",
        )

    json_candidate = _extract_json_candidate(content)
    if json_candidate is not None:
        return _parse_json_action(json_candidate)

    matches = list(
        re.finditer(
            r"Action:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*(\{.*?\})\s*\)",
            content,
            flags=re.DOTALL,
        )
    )
    if not matches:
        raise ActionParseError(
            "NO_ACTION",
            "Expected Action: tool_name({...}) or JSON action object.",
        )
    if len(matches) > 1:
        raise ActionParseError(
            "MULTIPLE_ACTIONS",
            "Expected exactly one action, but the model emitted multiple actions.",
        )

    match = matches[0]
    tool_name = match.group(1)
    raw_args = match.group(2)
    try:
        args = json.loads(raw_args)
    except json.JSONDecodeError as exc:
        raise ActionParseError("MALFORMED_JSON", str(exc)) from exc
    if not isinstance(args, dict):
        raise ActionParseError("INVALID_ARGUMENTS", "Action arguments must be a JSON object.")
    return ParsedAction(tool_name=tool_name, arguments=args, raw=match.group(0))


def _extract_json_candidate(content: str) -> Optional[str]:
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, flags=re.DOTALL | re.IGNORECASE)
    if fence is not None:
        return fence.group(1).strip()

    stripped = content.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    return None


def _parse_json_action(raw_json: str) -> ParsedAction:
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ActionParseError("MALFORMED_JSON", str(exc)) from exc

    if not isinstance(payload, dict):
        raise ActionParseError("INVALID_ACTION", "JSON action must be an object.")

    tool_name = payload.get("tool_name") or payload.get("tool") or payload.get("action")
    args = payload.get("arguments", payload.get("args", {}))

    if not isinstance(tool_name, str) or not tool_name.strip():
        raise ActionParseError("EMPTY_ACTION_NAME", "JSON action is missing a tool name.")
    if not isinstance(args, dict):
        raise ActionParseError("INVALID_ARGUMENTS", "JSON action arguments must be an object.")

    return ParsedAction(tool_name=tool_name.strip(), arguments=args, raw=raw_json)
