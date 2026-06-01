import re
from typing import Any, Callable, Dict, List


ValidationResult = Dict[str, Any]


def validate_case(answer: str, events: List[Dict[str, Any]], test_case: Dict[str, Any]) -> ValidationResult:
    """Run the deterministic validator declared by a test case."""
    validator_name = test_case["validator"]
    validators: Dict[str, Callable[[str, List[Dict[str, Any]], Dict[str, Any]], ValidationResult]] = {
        "contains_keywords": validate_contains_keywords,
        "order_total": validate_structured_order_total,
        "tool_sequence": validate_tool_sequence,
        "error_handling": validate_error_handling,
        "no_tool_call": validate_no_tool_call,
    }
    if validator_name not in validators:
        return _result(False, f"Unknown validator: {validator_name}")

    base = validators[validator_name](answer, events, test_case)
    sequence = validate_tool_sequence(answer, events, test_case)
    if not sequence["passed"]:
        return _result(False, f"{base['reason']}; {sequence['reason']}")
    return base


def validate_contains_keywords(answer: str, events: List[Dict[str, Any]], test_case: Dict[str, Any]) -> ValidationResult:
    """Pass when every expected keyword appears in the final answer."""
    expected = test_case.get("expected", {})
    missing = [
        keyword
        for keyword in expected.get("keywords", [])
        if not _contains_token(answer, str(keyword))
    ]
    if missing:
        return _result(False, f"Missing keyword(s): {', '.join(missing)}")
    return _result(True, "All expected keywords were found.")


def validate_structured_order_total(answer: str, events: List[Dict[str, Any]], test_case: Dict[str, Any]) -> ValidationResult:
    """Validate full-order tasks using tool result plus final answer text."""
    expected = test_case.get("expected", {})
    final_total = expected.get("final_total_vnd")
    if final_total is None:
        return _result(False, "Missing expected.final_total_vnd.")

    total_from_tool = _find_order_total_from_tool(events)
    answer_has_total = _contains_token(answer, _format_vnd(final_total)) or _contains_token(answer, str(final_total))
    tool_has_total = total_from_tool == final_total

    if not answer_has_total and not tool_has_total:
        return _result(False, f"Final total {final_total} not found in answer or tool result.")

    for field in ["subtotal_vnd", "shipping_fee_vnd"]:
        if field in expected:
            value = expected[field]
            if _contains_token(answer, _format_vnd(value)) or _contains_token(answer, str(value)):
                continue
            tool_value = _find_field_from_tool(events, field)
            if tool_value != value:
                return _result(False, f"Expected {field}={value} was not found.")

    return _result(True, "Expected order total matched deterministic values.")


def validate_tool_sequence(answer: str, events: List[Dict[str, Any]], test_case: Dict[str, Any]) -> ValidationResult:
    """Validate required and forbidden tool calls."""
    sequence = _tool_sequence(events)
    missing = [tool for tool in test_case.get("required_tools", []) if tool not in sequence]
    forbidden = [tool for tool in test_case.get("forbidden_tools", []) if tool in sequence]

    if missing:
        return _result(False, f"Missing required tool(s): {', '.join(missing)}")
    if forbidden:
        return _result(False, f"Forbidden tool(s) called: {', '.join(forbidden)}")
    return _result(True, "Tool sequence matched requirements.")


def validate_error_handling(answer: str, events: List[Dict[str, Any]], test_case: Dict[str, Any]) -> ValidationResult:
    """Pass when answer or tool results show the expected error/limitation."""
    expected = test_case.get("expected", {})
    answer_ok = validate_contains_keywords(answer, events, test_case)
    if answer_ok["passed"]:
        return answer_ok

    error_text = " ".join(_tool_error_messages(events))
    missing = [
        keyword
        for keyword in expected.get("keywords", [])
        if not _contains_token(error_text, str(keyword)) and not _contains_token(answer, str(keyword))
    ]
    if missing:
        return _result(False, f"Expected error keyword(s) missing: {', '.join(missing)}")
    return _result(True, "Expected error handling appeared in answer or tool result.")


def validate_no_tool_call(answer: str, events: List[Dict[str, Any]], test_case: Dict[str, Any]) -> ValidationResult:
    """Pass when no tool was called."""
    sequence = _tool_sequence(events)
    if sequence:
        return _result(False, f"Expected no tool calls, got: {' -> '.join(sequence)}")
    return _result(True, "No tool calls were made.")


def summarize_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute deterministic metrics from captured events."""
    llm_events = [event for event in events if event.get("event") == "LLM_METRIC"]
    tool_calls = [event for event in events if event.get("event") == "TOOL_CALL"]
    parser_errors = [event for event in events if event.get("event") == "PARSER_ERROR"]
    retries = [event for event in events if event.get("event") == "RETRY"]
    provider_errors = [event for event in events if event.get("event") == "PROVIDER_ERROR"]
    agent_end = next((event for event in reversed(events) if event.get("event") == "AGENT_END"), None)

    return {
        "llm_calls": len(llm_events),
        "tool_calls": len(tool_calls),
        "tool_sequence": " -> ".join(_tool_sequence(events)),
        "total_tokens": sum(int(_data(event).get("total_tokens", 0)) for event in llm_events),
        "total_latency_ms": sum(int(_data(event).get("latency_ms", 0)) for event in llm_events),
        "parser_errors": len(parser_errors),
        "retries": len(retries),
        "provider_errors": len(provider_errors),
        "termination_reason": _data(agent_end).get("termination_reason") if agent_end else "",
    }


def _tool_sequence(events: List[Dict[str, Any]]) -> List[str]:
    return [
        str(_data(event).get("tool_name"))
        for event in events
        if event.get("event") == "TOOL_CALL" and _data(event).get("tool_name")
    ]


def _find_order_total_from_tool(events: List[Dict[str, Any]]) -> Any:
    return _find_field_from_tool(events, "final_total_vnd")


def _find_field_from_tool(events: List[Dict[str, Any]], field: str) -> Any:
    for event in reversed(events):
        if event.get("event") != "TOOL_RESULT":
            continue
        data = _data(event)
        result = data.get("result", {})
        payload = result.get("data", {}) if isinstance(result, dict) else {}
        if field in payload:
            return payload[field]
    return None


def _tool_error_messages(events: List[Dict[str, Any]]) -> List[str]:
    messages = []
    for event in events:
        if event.get("event") not in {"TOOL_RESULT", "INVALID_ARGUMENTS", "UNKNOWN_TOOL"}:
            continue
        data = _data(event)
        result = data.get("result", data)
        error = result.get("error") if isinstance(result, dict) else None
        if isinstance(error, dict):
            messages.append(f"{error.get('code', '')} {error.get('message', '')}")
    return messages


def _contains_token(text: str, token: str) -> bool:
    normalized_text = _normalize(text)
    normalized_token = _normalize(token)
    if normalized_token in normalized_text:
        return True
    digits = re.sub(r"\D", "", token)
    if digits and digits in re.sub(r"\D", "", text):
        return True
    return False


def _normalize(value: Any) -> str:
    return str(value).lower().replace(",", "").strip()


def _format_vnd(value: int) -> str:
    return f"{value:,}"


def _data(event: Dict[str, Any] | None) -> Dict[str, Any]:
    if not event:
        return {}
    data = event.get("data", {})
    return data if isinstance(data, dict) else {}


def _result(passed: bool, reason: str) -> ValidationResult:
    return {"passed": passed, "reason": reason}
