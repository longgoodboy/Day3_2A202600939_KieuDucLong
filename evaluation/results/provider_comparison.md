# Benchmark Summary

Deterministic validators were used. No LLM-as-a-judge scoring was used.

## Overall Results

| Mode | Provider | Cases | Skipped | Evaluated | Passed | Success Rate | Avg Tokens | Avg Latency ms | Parser Errors | Retries | Provider Errors |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agent-v2 | gemini | 5 | 0 | 5 | 5 | 100.0% | 1190 | 1414 | 0 | 0 | 0 |

## Case Details

| Case | Category | Mode | Provider | Passed | Reason | Tool Sequence |
| --- | --- | --- | --- | --- | --- | --- |
| B02 | product_details | agent-v2 | gemini | True | All expected keywords were found. | get_product_details |
| B03 | stock | agent-v2 | gemini | True | All expected keywords were found. | check_stock |
| B05 | coupon | agent-v2 | gemini | True | All expected keywords were found. | get_discount |
| B08 | shipping | agent-v2 | gemini | True | All expected keywords were found. | calc_shipping |
| B15 | search | agent-v2 | gemini | True | All expected keywords were found. | search_products |

## Notes

- Business benchmark cases are separate from reliability tests.
- Reliability behaviors such as malformed JSON, markdown-fenced JSON, provider exception, and repeated action are covered by mock tests.
- MiMo Token Plan monetary cost is not estimated; token usage is still tracked.
