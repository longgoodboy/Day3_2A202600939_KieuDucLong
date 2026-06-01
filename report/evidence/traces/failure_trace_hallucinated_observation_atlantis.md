# Failure/Near-miss Trace: Hallucinated Observation and Unsupported Destination

## Context

- Date: 2026-06-01
- Mode: `agent-v1`
- Provider: `mimo`
- Model: `mimo-v2.5-pro`
- Log file: `logs/2026-06-01.log`
- Time window: `2026-06-01T10:17:15` to `2026-06-01T10:18:00`

This trace is useful because the raw MiMo output contains hallucinated observations that conflict with real tool results. The final answer was acceptable because Agent v1 executed real tools and fed real observations back, but the raw trace exposes a weakness that Agent v2 should guard more explicitly.

## Command

```powershell
python main.py --mode agent-v1 --provider mimo --prompt "I want to buy 2 iPhone 15 devices using code WINNER and ship to Atlantis. What is the final total?"
```

## User Input

```text
I want to buy 2 iPhone 15 devices using code WINNER and ship to Atlantis. What is the final total?
```

## Raw LLM Failure Symptom

In step 1, MiMo wrote its own `Observation` values before the runtime executed tools:

```text
Observation: {"product_id": "IP15", "name": "iPhone 15", "unit_price": 22000000, "stock": 15, "weight_kg": 0.5}
```

These values conflict with the real tool result:

```json
{"product_id":"P001","name":"iPhone 15","price_vnd":20000000,"stock":12,"weight_kg":0.35}
```

MiMo also computed shipping weight from hallucinated weight:

```text
Total weight = 0.5 kg * 2 = 1 kg
```

The runtime executed:

```json
{"tool_name":"calc_shipping","arguments":{"weight_kg":1,"destination":"Atlantis"}}
```

The real tool result was an error:

```json
{"status":"error","error":{"code":"UNSUPPORTED_DESTINATION","message":"Unsupported destination: Atlantis"}}
```

## Final Answer

The final answer correctly refused to compute a final total:

```text
Shipping to Atlantis is not supported, so the shipping fee cannot be calculated, and the final total is unavailable.
```

## Root Cause

Agent v1 uses text-based ReAct parsing. MiMo sometimes does not obey the instruction to stop after one action. It may write:

- multiple actions in one response;
- fake observations;
- a premature final answer;
- argument values derived from fake observations.

The current Agent v1 mitigates part of this by executing the parsed actions and feeding real observations back. However, it does not fully validate whether later action arguments were derived from hallucinated observations in the same raw output.

## Planned Agent v2 Fix

Agent v2 should:

- parse one action at a time or require strict JSON action format;
- reject model-written `Observation` blocks;
- validate tool arguments against trusted state when possible;
- prefer canonical tool outputs over raw LLM claims;
- add retry feedback when output contains both action and hallucinated observation;
- log `PARSER_ERROR` or `INVALID_ARGUMENTS` for malformed/mixed ReAct output.

## Why This Trace Matters

This is a strong debugging case study because the trace shows the difference between:

- what the LLM claimed;
- what tools actually returned;
- how the agent recovered enough to produce a safe answer;
- what v2 should improve for reliability.
