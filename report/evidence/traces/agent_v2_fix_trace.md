# Agent v2 Fix Trace: Provider Error Handling

## Context

- Date: 2026-06-01
- Mode: `agent-v2`
- Provider: `mimo`
- Model: `mimo-v2.5-pro`
- Log file: `logs/2026-06-01.log`
- Time window: `2026-06-01T10:30:04` to `2026-06-01T10:30:15`

This trace compares a real Agent v1 failure from Phase 4 with the Agent v2 fix.

## Before: Agent v1 Failure

Agent v1 failure trace:

```text
report/evidence/traces/failure_trace_provider_rate_limit.md
```

Symptom:

```text
openai.RateLimitError: Error code: 429 - Too many requests
```

Agent v1 behavior:

- crashed in `llm.generate`;
- did not retry;
- did not log `PROVIDER_ERROR`;
- did not log `AGENT_END`;
- returned no useful user-facing fallback.

## After: Agent v2 Behavior

Command:

```powershell
python main.py --mode agent-v2 --provider mimo --prompt "I want to buy 2 iPhone 15 devices using code WINNER and ship to Hanoi. What is the final total?"
```

User-facing output:

```text
I cannot complete the request right now because the model provider is unavailable or rate-limited. Please retry in a moment.
```

Important log sequence:

```text
AGENT_START
LLM_METRIC
AGENT_STEP
TOOL_CALL get_product_details
TOOL_RESULT get_product_details
PROVIDER_ERROR attempt=1
RETRY reason=provider_error
PROVIDER_ERROR attempt=2
RETRY reason=provider_error
PROVIDER_ERROR attempt=3
AGENT_END termination_reason=provider_error
```

Key log snippets:

```json
{"event":"PROVIDER_ERROR","data":{"step":2,"attempt":1,"provider":"mimo","model":"mimo-v2.5-pro","error_type":"RateLimitError","message":"Error code: 429 - ... Too many requests ..."}}
```

```json
{"event":"RETRY","data":{"step":2,"attempt":1,"reason":"provider_error"}}
```

```json
{"event":"AGENT_END","data":{"version":"v2","steps":1,"termination_reason":"provider_error"}}
```

## Fix Implemented

Agent v2 catches provider exceptions around `llm.generate`.

Implemented behavior:

- log `PROVIDER_ERROR` with provider, model, error type, and message;
- retry transient provider failures up to `max_retries=2`;
- return a graceful fallback answer after retries are exhausted;
- always log `AGENT_END` with `termination_reason="provider_error"`.

## Additional Regression Coverage

Mock regression tests also cover the other Phase 4 near-miss:

- model-written `Observation`;
- markdown-fenced JSON;
- unknown tool;
- wrong argument type;
- missing argument;
- repeated action;
- provider exception.

Test command:

```powershell
pytest tests/test_parser.py tests/test_agent_v2.py
```

Result:

```text
14 passed
```

Full current test suite:

```text
57 passed
```

## Follow-up Fix: Repeated Information Tool Actions

During benchmark reruns, Agent v2 sometimes repeated an already completed information action such as `get_product_details` after receiving valid observations. The initial guardrail stopped safely, but stopped too early to complete the order.

Additional fix:

- cache successful tool observations by action signature;
- when the same action repeats once, feed the cached observation back with an instruction to move to the next required action;
- only stop if the same action repeats again without progress.

Regression coverage:

```text
tests/test_agent_v2.py::test_agent_v2_reuses_cached_observation_once_before_stopping
```

After this fix, MiMo Agent v2 completed benchmark case `B11`:

```text
get_product_details -> get_discount -> check_stock -> calc_shipping -> calculate_order_total
Final total: 36,037,000 VND
AGENT_END termination_reason=final_answer
```

Benchmark summary:

```text
agent-v2 + mimo
B11 full_order
passed: 1/1
success rate: 100%
```
