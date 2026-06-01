MARKDOWN_FENCED_ACTION = """```json
{"tool_name": "lookup", "arguments": {"item_name": "iPhone 15"}}
```"""

MODEL_WRITTEN_OBSERVATION = """Thought: I know what to do.
Action: lookup({"item_name": "iPhone 15"})
Observation: {"price_vnd": 99999999}
Final Answer: fake answer"""

MALFORMED_JSON_ACTION = 'Action: lookup({"item_name": "iPhone 15"'

UNKNOWN_TOOL_ACTION = 'Action: made_up({"item_name": "iPhone 15"})'

WRONG_ARGUMENT_TYPE = 'Action: lookup({"item_name": 123})'

MISSING_ARGUMENT = 'Action: lookup({})'

REPEATED_ACTION = 'Action: lookup({"item_name": "iPhone 15"})'
