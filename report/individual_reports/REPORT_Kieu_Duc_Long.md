# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Kieu Duc Long
- **Student ID**: 2A202600939
- **Date**: 2026-06-01

## I. Technical Contribution

I implemented the full solo project from provider foundation to reports.

Main modules:

- `src/core/mimo_provider.py`
- `src/core/provider_factory.py`
- `src/core/gemini_provider.py`
- `src/tools/ecommerce_tools.py`
- `src/tools/registry.py`
- `src/chatbot.py`
- `src/agent/agent.py`
- `src/agent/parsers.py`
- `src/agent/agent_v2.py`
- `evaluation/validators.py`
- `evaluation/run_benchmark.py`
- `evaluation/analyze_results.py`

Tests added:

- `tests/test_provider_factory.py`
- `tests/test_tools.py`
- `tests/test_chatbot.py`
- `tests/test_telemetry.py`
- `tests/test_agent_v1.py`
- `tests/test_parser.py`
- `tests/test_agent_v2.py`
- `tests/test_evaluation.py`

Current test status:

```text
57 passed
```

Key engineering choices:

- MiMo is treated as a first-class provider, not mislabeled as OpenAI.
- API keys are loaded from `.env`; no secrets are hard-coded.
- Tool outputs use a consistent `status/data/error` schema.
- Agent v2 fixes are based on real logs from Agent v1, not guesswork.
- Benchmark scoring uses deterministic validators, not LLM-as-a-judge.

## II. Debugging Case Study

### Problem

Agent v1 crashed when MiMo returned a provider rate-limit error:

```text
openai.RateLimitError: Error code: 429 - Too many requests
```

Trace:

```text
report/evidence/traces/failure_trace_provider_rate_limit.md
```

### Log Evidence

Agent v1 logged:

```text
AGENT_START
```

Then the process crashed before:

```text
AGENT_END
```

This made the trace incomplete and would make live demo/benchmark unreliable.

### Diagnosis

Root cause:

- Agent v1 called `self.llm.generate(...)` directly.
- It did not catch provider exceptions.
- Rate limit is an external provider condition, but the application still needs graceful handling.

Impact:

- No retry.
- No fallback answer.
- No `PROVIDER_ERROR`.
- No controlled `AGENT_END`.

### Solution

Agent v2 adds provider error handling:

- catches exceptions around `llm.generate`;
- logs `PROVIDER_ERROR`;
- retries up to `max_retries`;
- returns a helpful fallback when retries fail;
- always logs `AGENT_END` with a termination reason.

Fix evidence:

```text
report/evidence/traces/agent_v2_fix_trace.md
```

In a later live run, Agent v2 encountered a `429` during the final answer step, retried, and still produced:

```text
36,037,000 VND
```

This showed the improvement was real, not only a unit test artifact.

## III. Personal Insights: Chatbot vs ReAct

### Reasoning

The chatbot is fast and simple because it uses one LLM call. However, for e-commerce questions, it can invent price, stock, shipping, or coupon facts.

The ReAct agent is slower, but the action/observation loop grounds the answer in tool results. For the order query, the agent used real product price, coupon discount, and shipping fee before answering.

### Reliability

Agent v1 can perform worse than a chatbot when:

- the model emits malformed action text;
- the model writes fake observations;
- the model repeats the same action;
- the provider rate-limits in the middle of a loop.

This is why observability matters. The trace showed not only that the answer failed, but exactly where and why it failed.

### Observation Feedback

Observations are the key difference. Once the tool returns:

```json
{"shipping_fee_vnd": 37000}
```

the agent can compute the correct final total. Without observations, the model may guess a plausible but wrong shipping fee.

## IV. Future Improvements

Scalability:

- Add async execution and queueing for long-running benchmarks.
- Use provider-specific backoff based on retry delay from error responses.
- Add a persistent `trace_id` per run for easier log slicing.

Safety:

- Add stronger argument schemas with Pydantic.
- Add a supervisor step before high-impact actions such as order placement.
- Redact sensitive data in logs by default.

Performance:

- Add a composite `quote_order` tool to reduce multi-step LLM calls.
- Cache deterministic tool results within a session.
- Use smaller models for simple tool-routing cases and MiMo for complex reasoning.

Production:

- Move from CLI to an API service.
- Store traces in a database or observability backend.
- Add dashboard metrics for success rate, P50/P95 latency, retry rate, and provider errors.
