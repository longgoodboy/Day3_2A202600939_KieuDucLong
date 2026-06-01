# Group Report - Solo Team

Student: Kieu Duc Long

## Scope

This submission keeps the repository in the required Lab 3 structure:

- `src/chatbot.py`: chatbot baseline, one LLM call, no tools.
- `src/agent/agent.py`: ReAct loop with Thought, Action, and Observation.
- `src/tools/`: e-commerce tools for product lookup, stock, coupons, shipping, order total, and search.
- `src/core/`: shared LLM provider interface plus OpenAI and Gemini providers.
- `src/telemetry/`: logging and metrics helpers.
- `tests/`: unit tests comparing baseline behavior, agent loop behavior, tools, and telemetry.
- `report/group_report/` and `report/individual_reports/`: submission reports.

## Chatbot vs Agent

The chatbot baseline calls the LLM once and does not execute tools. It is useful for direct answers but can hallucinate product, stock, coupon, or shipping facts.

The ReAct agent receives the same user request but can call tools, append real observations, and answer from structured results. This makes it more reliable for order and product workflows.

## Tools

Implemented tools:

- `search_products`
- `get_product_details`
- `check_stock`
- `get_discount`
- `calc_shipping`
- `calculate_order_total`

All tool outputs use the same `status`, `data`, and `error` shape.

## Tests

The remaining tests focus on the required structure:

```text
pytest tests
```

They cover:

- chatbot calls the LLM exactly once;
- chatbot does not call tools;
- ReAct agent handles actions, observations, parser errors, unknown tools, and max steps;
- tools return deterministic structured results;
- telemetry records provider, model, tokens, and latency.

## Notes

No API key is stored in the repository. Local secrets stay in `.env`, which is ignored by Git.
