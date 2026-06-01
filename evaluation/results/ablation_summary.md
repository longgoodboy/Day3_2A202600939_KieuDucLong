# Ablation Summary

Status: scaffold prepared, full ablation run pending.

Prepared configs:

- `evaluation/configs/tool_specs_v1.json`
- `evaluation/configs/tool_specs_v2.json`
- `evaluation/configs/prompt_v1.txt`
- `evaluation/configs/prompt_v2.txt`

Planned experiments:

| Experiment | Config A | Config B | Subset |
| --- | --- | --- | --- |
| Tool description quality | `tool_specs_v1.json` | `tool_specs_v2.json` | 5-10 business cases |
| Prompt format | `prompt_v1.txt` | `prompt_v2.txt` | 5-10 business cases |

Metrics to report:

- success rate;
- parser errors;
- wrong-tool calls;
- retry count;
- average steps;
- average latency;
- average tokens.

Note: this file is intentionally marked pending until the main MiMo benchmark is stable enough to run without frequent rate limits.
