# Individual Report - Kieu Duc Long

## Contribution

I implemented and simplified the Lab 3 submission into the requested structure:

- chatbot baseline in `src/chatbot.py`;
- ReAct agent loop in `src/agent/agent.py`;
- reusable e-commerce tools in `src/tools/`;
- provider interface plus OpenAI and Gemini providers in `src/core/`;
- telemetry logger and metrics tracking in `src/telemetry/`;
- tests under `tests/`.

## Implementation Summary

The chatbot baseline makes one LLM call and returns the response directly.

The agent uses a ReAct loop:

```text
Thought -> Action -> Observation -> Final Answer
```

When the model emits an action, the runtime executes the matching Python tool and feeds the structured observation back to the model. The agent also handles parser errors, unknown tools, invalid arguments, and max-step termination.

## Testing

The submission can be checked with:

```text
pytest tests
```

The tests verify chatbot behavior, ReAct agent behavior, tool correctness, and telemetry fields.

## Secret Safety

API keys are not committed. The local `.env` file is ignored by Git.
