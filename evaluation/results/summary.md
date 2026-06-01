# Benchmark Summary

Deterministic validators were used. No LLM-as-a-judge scoring was used.

## Overall Results

| Mode | Provider | Cases | Skipped | Evaluated | Passed | Success Rate | Avg Tokens | Avg Latency ms | Parser Errors | Retries | Provider Errors |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agent-v2 | mimo | 1 | 0 | 1 | 1 | 100.0% | 5755 | 49445 | 0 | 0 | 0 |

## Case Details

| Case | Category | Mode | Provider | Passed | Reason | Tool Sequence |
| --- | --- | --- | --- | --- | --- | --- |
| B11 | full_order | agent-v2 | mimo | True | Expected order total matched deterministic values. | get_product_details -> get_discount -> check_stock -> calc_shipping -> calculate_order_total |

## Notes

- Business benchmark cases are separate from reliability tests.
- Reliability behaviors such as malformed JSON, markdown-fenced JSON, provider exception, and repeated action are covered by mock tests.
- MiMo Token Plan monetary cost is not estimated; token usage is still tracked.
