# Lab 3: Chatbot vs ReAct Agent

Smart E-commerce Assistant for comparing:

- baseline chatbot;
- Agent v1 ReAct loop;
- Agent v2 robust ReAct loop with retry, validation, and guardrails.

Primary provider: MiMo `mimo-v2.5-pro`.

Secondary provider: Gemini `gemini-3.1-flash-lite`.

## Setup

```powershell
cd D:\vin_lab\Day-3-Lab-Chatbot-vs-react-agent
pip install -r requirements.txt
copy .env.example .env
```

Fill `.env` locally. Do not paste API keys into chat or commit them.

Required for MiMo:

```env
DEFAULT_PROVIDER=mimo
MIMO_API_KEY=
MIMO_BASE_URL=https://token-plan-sgp.xiaomimimo.com/v1
MIMO_MODEL=mimo-v2.5-pro
```

Optional secondary provider:

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.1-flash-lite
```

## Run Modes

Chatbot baseline:

```powershell
python main.py --mode chatbot --provider mimo --prompt "What products do you sell?"
```

Agent v1:

```powershell
python main.py --mode agent-v1 --provider mimo --prompt "I want to buy 2 iPhone 15 devices using code WINNER and ship to Hanoi. What is the final total?"
```

Agent v2:

```powershell
python main.py --mode agent-v2 --provider mimo --prompt "I want to buy 2 iPhone 15 devices using code WINNER and ship to Hanoi. What is the final total?"
```

Gemini provider switching:

```powershell
python main.py --mode agent-v2 --provider gemini --prompt "How much is shipping 0.7 kg to Hanoi?"
```

Interactive mode:

```powershell
python main.py --mode agent-v2 --provider mimo --interactive
```

## Expected Demo Answer

For:

```text
I want to buy 2 iPhone 15 devices using code WINNER and ship to Hanoi. What is the final total?
```

Expected deterministic total:

```text
36,037,000 VND
```

Calculation:

```text
2 * 20,000,000 = 40,000,000
10% discount = 4,000,000
shipping 0.7 kg to Hanoi = 37,000
final total = 36,037,000 VND
```

## Logs

Logs are written as JSON lines under:

```text
logs/
```

View latest log tail:

```powershell
$log = Get-ChildItem .\logs\*.log | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content $log.FullName -Tail 120
```

Useful event filters:

```powershell
Get-Content .\logs\2026-06-01.log | Select-String '"event": "TOOL_CALL"'
Get-Content .\logs\2026-06-01.log | Select-String '"event": "LLM_METRIC"'
Get-Content .\logs\2026-06-01.log | Select-String '"event": "PROVIDER_ERROR"'
```

Important event types:

- `CHATBOT_START`, `CHATBOT_END`
- `AGENT_START`, `AGENT_STEP`, `AGENT_END`
- `LLM_METRIC`
- `TOOL_CALL`, `TOOL_RESULT`
- `PARSER_ERROR`, `PROVIDER_ERROR`, `RETRY`, `REPEATED_ACTION`
- `FINAL_ANSWER`, `MAX_STEPS_EXCEEDED`

## Tests

```powershell
pytest tests/test_evaluation.py tests/test_parser.py tests/test_agent_v2.py tests/test_agent_v1.py tests/test_chatbot.py tests/test_telemetry.py tests/test_provider_factory.py tests/test_tools.py
```

Current expected status:

```text
57 passed
```

## Benchmark

Run one MiMo smoke case:

```powershell
python evaluation/run_benchmark.py --provider mimo --mode agent-v2 --case-id B11 --request-delay 25 --agent-max-retries 1 --output evaluation/results/benchmark_results.csv
python evaluation/analyze_results.py --input evaluation/results/benchmark_results.csv --output evaluation/results/summary.md
```

Run provider comparison with Gemini:

```powershell
python evaluation/run_benchmark.py --provider gemini --mode agent-v2 --case-ids B02,B03,B05,B08,B15 --request-delay 15 --agent-max-retries 0 --output evaluation/results/provider_comparison.csv
python evaluation/analyze_results.py --input evaluation/results/provider_comparison.csv --output evaluation/results/provider_comparison.md
```

Benchmark rules:

- Business benchmark uses deterministic validators.
- Reliability tests use fake/mock providers.
- No LLM-as-a-judge scoring is used.

## Evidence

Trace evidence:

```text
report/evidence/traces/success_trace_multi_step.md
report/evidence/traces/failure_trace_provider_rate_limit.md
report/evidence/traces/failure_trace_hallucinated_observation_atlantis.md
report/evidence/traces/agent_v2_fix_trace.md
```

Reports:

```text
report/group_report/GROUP_REPORT_Solo_Kieu_Duc_Long.md
report/individual_reports/REPORT_Kieu_Duc_Long.md
```

Benchmark outputs:

```text
evaluation/results/benchmark_results.csv
evaluation/results/summary.md
evaluation/results/provider_comparison.csv
evaluation/results/provider_comparison.md
evaluation/results/ablation_results.csv
evaluation/results/ablation_summary.md
```

## Secret Safety

Before submission:

```powershell
git status
git check-ignore .env
git grep -n "t[p]-"
git grep -n "s[k]-"
```

Expected:

```text
.env is ignored
no tracked MiMo keys
no tracked OpenAI keys
```

## Notes

MiMo Token Plan cost is not reported as `0.0`. Telemetry uses:

```json
{
  "cost_estimate": null,
  "cost_note": "N/A: token-plan quota"
}
```
