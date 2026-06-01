import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures"))

import pytest

from src.agent.parsers import ActionParseError, parse_final_answer, parse_single_action
import llm_outputs


def test_parse_action_text_format():
    action = parse_single_action('Thought: x\nAction: lookup({"item_name": "iPhone 15"})')

    assert action.tool_name == "lookup"
    assert action.arguments == {"item_name": "iPhone 15"}


def test_parse_markdown_fenced_json_action():
    action = parse_single_action(llm_outputs.MARKDOWN_FENCED_ACTION)

    assert action.tool_name == "lookup"
    assert action.arguments == {"item_name": "iPhone 15"}


def test_parse_raw_json_action():
    action = parse_single_action('{"tool": "lookup", "args": {"item_name": "iPhone 15"}}')

    assert action.tool_name == "lookup"
    assert action.arguments == {"item_name": "iPhone 15"}


def test_model_written_observation_is_rejected():
    with pytest.raises(ActionParseError) as exc_info:
        parse_single_action(llm_outputs.MODEL_WRITTEN_OBSERVATION)

    assert exc_info.value.code == "MODEL_WRITTEN_OBSERVATION"


def test_multiple_actions_are_rejected():
    output = (
        'Action: lookup({"item_name": "iPhone 15"})\n'
        'Action: lookup({"item_name": "Laptop Air 13"})'
    )

    with pytest.raises(ActionParseError) as exc_info:
        parse_single_action(output)

    assert exc_info.value.code == "MULTIPLE_ACTIONS"


def test_malformed_json_is_rejected():
    with pytest.raises(ActionParseError) as exc_info:
        parse_single_action(llm_outputs.MALFORMED_JSON_ACTION)

    assert exc_info.value.code == "NO_ACTION"


def test_final_answer_parser():
    assert parse_final_answer("Thought: done\nFinal Answer: hello") == "hello"
    assert parse_final_answer("hello") is None
