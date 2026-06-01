import json
import os
import sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.validators import summarize_events, validate_case


ROOT_DIR = Path(__file__).resolve().parents[1]


def test_test_cases_are_business_cases_with_expected_and_validator():
    test_cases = json.loads((ROOT_DIR / "evaluation" / "test_cases.json").read_text(encoding="utf-8"))

    assert len(test_cases) >= 20
    for test_case in test_cases:
        assert test_case["id"].startswith("B")
        assert "expected" in test_case
        assert "validator" in test_case
        assert "query" in test_case
        assert "required_tools" in test_case
        assert "forbidden_tools" in test_case


def test_order_total_validator_uses_tool_result_and_tool_sequence():
    test_case = {
        "validator": "order_total",
        "expected": {
            "subtotal_vnd": 40000000,
            "shipping_fee_vnd": 37000,
            "final_total_vnd": 36037000,
        },
        "required_tools": ["calculate_order_total"],
        "forbidden_tools": [],
    }
    events = [
        {"event": "TOOL_CALL", "data": {"tool_name": "calculate_order_total"}},
        {
            "event": "TOOL_RESULT",
            "data": {
                "tool_name": "calculate_order_total",
                "result": {
                    "status": "success",
                    "data": {
                        "subtotal_vnd": 40000000,
                        "shipping_fee_vnd": 37000,
                        "final_total_vnd": 36037000,
                    },
                    "error": None,
                },
            },
        },
    ]

    result = validate_case("The final total is 36,037,000 VND.", events, test_case)

    assert result["passed"] is True


def test_tool_sequence_validator_catches_missing_required_tool():
    test_case = {
        "validator": "contains_keywords",
        "expected": {"keywords": ["iPhone"]},
        "required_tools": ["get_product_details"],
        "forbidden_tools": [],
    }

    result = validate_case("iPhone", [], test_case)

    assert result["passed"] is False
    assert "Missing required tool" in result["reason"]


def test_summarize_events_counts_tokens_retries_and_provider_errors():
    events = [
        {"event": "LLM_METRIC", "data": {"total_tokens": 10, "latency_ms": 100}},
        {"event": "TOOL_CALL", "data": {"tool_name": "get_discount"}},
        {"event": "RETRY", "data": {"reason": "provider_error"}},
        {"event": "PROVIDER_ERROR", "data": {"error_type": "RateLimitError"}},
        {"event": "AGENT_END", "data": {"termination_reason": "provider_error"}},
    ]

    summary = summarize_events(events)

    assert summary["total_tokens"] == 10
    assert summary["total_latency_ms"] == 100
    assert summary["tool_sequence"] == "get_discount"
    assert summary["retries"] == 1
    assert summary["provider_errors"] == 1
    assert summary["termination_reason"] == "provider_error"
