# Failure Trace: Provider Rate Limit Crash

## Context

- Date: 2026-06-01
- Mode: `agent-v1`
- Provider: `mimo`
- Model: `mimo-v2.5-pro`
- Log file: `logs/2026-06-01.log`
- Time: `2026-06-01T10:18:55`

This is a real Agent v1 + MiMo failure. The failure was not mocked.

## Command

```powershell
python main.py --mode agent-v1 --provider mimo --prompt "I want to buy 2 iPhone 15 devices using coupon FAKECODE and ship to Hanoi. What is the final total?"
```

## User Input

```text
I want to buy 2 iPhone 15 devices using coupon FAKECODE and ship to Hanoi. What is the final total?
```

## Failure Symptom

The CLI crashed before the first `AGENT_STEP`.

Terminal error:

```text
openai.RateLimitError: Error code: 429 - {'error': {'code': '429', 'message': 'Too many requests', 'type': 'limitation'}}
```

Log only contains `AGENT_START`; there is no `AGENT_END`.

```json
{"timestamp":"2026-06-01T10:18:55.438758","event":"AGENT_START","data":{"input":"I want to buy 2 iPhone 15 devices using coupon FAKECODE and ship to Hanoi. What is the final total?","provider":"mimo","model":"mimo-v2.5-pro","max_steps":8}}
```

## Root Cause

Agent v1 calls `self.llm.generate(...)` directly inside the ReAct loop without catching provider exceptions.

When MiMo returned HTTP `429 Too many requests`, the exception propagated to `main.py` and terminated the process. Because the exception was not handled inside the agent loop:

- no `PROVIDER_ERROR` event was logged;
- no retry occurred;
- no fallback user-facing answer was returned;
- no `AGENT_END` event was emitted.

This is a real reliability gap. The model/provider can fail even when the prompt and tools are valid.

## Impact

This failure hurts:

- Trace Quality: the trace is incomplete because `AGENT_END` is missing.
- Live Demo reliability: a temporary provider limit can crash the demo.
- Evaluation reliability: benchmark scripts would stop instead of marking the case failed/skipped.

## Planned Agent v2 Fix

Agent v2 should add provider error handling:

- catch provider exceptions around `llm.generate`;
- log `PROVIDER_ERROR` with provider, model, error type, and message;
- retry transient provider failures with a small retry limit;
- return a useful fallback answer if retries fail;
- always log `AGENT_END` with `termination_reason="provider_error"` when the run cannot continue.

Expected Agent v2 behavior:

```text
I cannot complete the request right now because the model provider is rate-limited. Please retry in a moment.
```

Expected Agent v2 logs:

```text
AGENT_START
PROVIDER_ERROR
RETRY
PROVIDER_ERROR
AGENT_END termination_reason=provider_error
```

## Why This Failure Is Useful

The instructor guide says to improve the system based on facts from logs, not intuition. This trace shows a concrete system-level failure that Agent v2 can fix with retry and graceful termination.
