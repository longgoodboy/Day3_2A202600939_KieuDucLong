# Summary hiện trạng Lab 3

File này tóm tắt những gì đã hoàn thành để giữ context ngắn gọn trước khi chuyển sang Phase 3.

## Docs đã tạo/cập nhật

- `plan.md`
- `phases.md`

Nội dung chính đã chốt:

- MiMo là primary provider.
- Gemini hoặc OpenAI là secondary provider trước submission.
- Business benchmark tách khỏi reliability tests.
- Reliability tests dùng mock/fake provider.
- Failure trace thật phải lấy từ Agent v1 + MiMo.
- Không dùng LLM-as-a-judge.
- MiMo Token Plan dùng `cost_estimate: null`, không ghi giả `0.0`.
- Có secret scan bằng `git grep`.

## Phase 0: Provider Foundation

Đã làm:

- Cập nhật `.env.example`.
- Tạo `src/core/mimo_provider.py`.
- Tạo `src/core/provider_factory.py`.
- Tạo `tests/test_provider_factory.py`.

Checks:

- MiMo smoke test thật đã pass.
- Provider log là `mimo`.
- Model là `mimo-v2.5-pro`.
- `.env` bị Git ignore.
- `git grep -n "tp\\-"` sạch.
- `git grep -n "sk\\-"` sạch.
- Provider tests pass.

MiMo smoke test output quan trọng:

```text
provider= mimo
model= mimo-v2.5-pro
content= MiMo smoke test OK
```

## Phase 1: Mock Data và Tools

Đã làm:

- Tạo `data/products.json`.
- Tạo `data/coupons.json`.
- Tạo `data/shipping_rates.json`.
- Tạo `src/tools/ecommerce_tools.py`.
- Tạo `src/tools/registry.py`.
- Tạo `src/tools/schemas.py`.
- Tạo `tests/test_tools.py`.

Tools đã có:

- `search_products`
- `get_product_details`
- `check_stock`
- `get_discount`
- `calc_shipping`
- `calculate_order_total`

Checks:

- Tool response thống nhất `status/data/error`.
- Invalid product/coupon/city/quantity/weight được handle.
- Order total cho 2 iPhone + WINNER + Hanoi ra `36,037,000 VND`.
- Tool tests pass.

## Phase 2: Chatbot Baseline, CLI và Telemetry

Đã làm:

- Tạo `src/chatbot.py`.
- Tạo `main.py`.
- Cập nhật `src/telemetry/metrics.py`.
- Tạo `tests/test_chatbot.py`.
- Tạo `tests/test_telemetry.py`.

Checks:

- Chatbot gọi LLM đúng 1 lần.
- Chatbot không gọi tools.
- CLI chạy được với MiMo.
- Logs có:
  - `CHATBOT_START`
  - `LLM_METRIC`
  - `CHATBOT_END`
- Telemetry có provider/model/token/latency.
- API key không bị log.
- MiMo cost policy:

```json
{
  "cost_estimate": null,
  "cost_note": "N/A: token-plan quota"
}
```

CLI smoke test:

```powershell
python main.py --mode chatbot --provider mimo --prompt "Reply with exactly: Chatbot phase 2 OK"
```

Output:

```text
Chatbot phase 2 OK
```

## Test status hiện tại

Lệnh đã chạy:

```powershell
pytest tests/test_chatbot.py tests/test_telemetry.py tests/test_provider_factory.py tests/test_tools.py
```

Kết quả:

```text
31 passed
```

## Git status hiện tại

Các file/thư mục đã thêm hoặc sửa chính:

- `.env.example`
- `plan.md`
- `phases.md`
- `summary.md`
- `main.py`
- `data/`
- `src/chatbot.py`
- `src/core/mimo_provider.py`
- `src/core/provider_factory.py`
- `src/tools/`
- `src/telemetry/metrics.py`
- `tests/test_chatbot.py`
- `tests/test_provider_factory.py`
- `tests/test_telemetry.py`
- `tests/test_tools.py`

## Tiếp theo: Phase 3

Phase tiếp theo là `Agent v1 ReAct Loop`.

Việc cần làm:

- Implement `src/agent/agent.py`.
- Parse `Final Answer`.
- Parse `Action: tool_name({...})`.
- Execute tool từ registry.
- Append `Observation` vào prompt.
- Enforce `max_steps`.
- Add `tests/test_agent_v1.py`.
- Chạy Agent v1 bằng MiMo sau khi unit tests pass.

## Phase 3: Agent v1 ReAct Loop

Đã làm:

- Implement `src/agent/agent.py`.
- Cập nhật `main.py` để hỗ trợ `--mode agent-v1`.
- Tạo `tests/test_agent_v1.py`.
- Agent v1 parse được:
  - `Final Answer: ...`
  - `Action: tool_name({...})`
  - nhiều `Action` trong cùng một LLM output.
- Agent v1 execute tool từ registry thật.
- Agent v1 append `Observation` thật vào prompt lượt sau.
- Agent v1 không feed lại observation/final do model tự viết trong cùng output.
- Agent v1 enforce `max_steps`.
- Agent v1 log:
  - `AGENT_START`
  - `AGENT_STEP`
  - `LLM_METRIC`
  - `TOOL_CALL`
  - `TOOL_RESULT`
  - `PARSER_ERROR`
  - `FINAL_ANSWER`
  - `MAX_STEPS_EXCEEDED`
  - `AGENT_END`

Tests:

```powershell
pytest tests/test_agent_v1.py tests/test_chatbot.py tests/test_telemetry.py tests/test_provider_factory.py tests/test_tools.py
```

Kết quả:

```text
38 passed
```

MiMo Agent v1 live run đã thành công với query:

```text
I want to buy 2 iPhone 15 devices using code WINNER and ship to Hanoi. What is the final total?
```

Output đúng:

```text
Final Total: 36,037,000 VND
```

Log quan trọng:

- Provider: `mimo`
- Model: `mimo-v2.5-pro`
- Termination: `final_answer`
- Steps: `7`
- Tools đã gọi trong trace thành công:
  - `search_products`
  - `get_discount`
  - `check_stock`
  - `calc_shipping`
  - `calculate_order_total`

Các lỗi thật quan sát được trong lúc chạy MiMo, có thể dùng cho Phase 4 failure trace/RCA:

- Có lần MiMo tự viết `Observation` và `Final Answer` trong cùng một response trước khi runtime execute tool.
- Có lần MiMo dùng shipping fee tự bịa `50,000 VND` dù tool thật trả `37,000 VND`.
- Có lần MiMo trả final answer không có marker `Final Answer:`, gây `PARSER_ERROR`.
- Có lúc provider trả `429 Too many requests`.

Fix nhẹ đã áp dụng ngay trong Agent v1:

- Nếu output có action, Agent execute action trước thay vì tin `Final Answer` trong cùng output.
- Nếu output có nhiều action, Agent execute lần lượt tất cả action.
- Prompt history chỉ giữ action và observation thật, không giữ observation/final tự bịa của model.

## Test status sau Phase 3

```text
38 passed
```

Secret checks sau Phase 3:

```text
git check-ignore .env -> .env
git grep -n "tp\\-" -> no tracked matches
git grep -n "sk\\-" -> no tracked matches
```

## Tiếp theo: Phase 4

Phase tiếp theo là `Run MiMo Agent v1, Capture Real Traces và Perform RCA`.

Việc cần làm:

- Lưu success trace thật từ run Agent v1 vừa thành công.
- Chạy các failure-oriented natural queries:
  - unsupported city `Atlantis`;
  - coupon `FAKECODE`;
  - buy `100 iPhone 15`;
  - query thiếu thông tin;
  - query mơ hồ dễ làm agent gọi sai tool hoặc truyền sai arguments.
- Chọn ít nhất một failure thật của Agent v1.
- Lưu failure trace và RCA vào `report/evidence/traces/`.

## Phase 4: Run MiMo Agent v1, Capture Real Traces va Perform RCA

Da lam:

- Tao thu muc `report/evidence/traces/`.
- Luu success trace that:
  - `report/evidence/traces/success_trace_multi_step.md`
- Luu failure trace that:
  - `report/evidence/traces/failure_trace_provider_rate_limit.md`
- Luu failure/near-miss trace phuc vu RCA:
  - `report/evidence/traces/failure_trace_hallucinated_observation_atlantis.md`

Success trace:

- Query:

```text
I want to buy 2 iPhone 15 devices using code WINNER and ship to Hanoi. What is the final total?
```

- Ket qua dung:

```text
Final Total: 36,037,000 VND
```

- Log co:
  - `AGENT_START`
  - `LLM_METRIC`
  - `AGENT_STEP`
  - `TOOL_CALL`
  - `TOOL_RESULT`
  - `FINAL_ANSWER`
  - `AGENT_END`

Failure trace 1:

- Query:

```text
I want to buy 2 iPhone 15 devices using coupon FAKECODE and ship to Hanoi. What is the final total?
```

- Failure:

```text
openai.RateLimitError: Error code: 429 - Too many requests
```

- RCA:
  - Agent v1 chua catch provider exception.
  - CLI crash truoc khi co `AGENT_END`.
  - Agent v2 can retry, log `PROVIDER_ERROR`, va ket thuc graceful voi `termination_reason=provider_error`.

Failure/near-miss trace 2:

- Query:

```text
I want to buy 2 iPhone 15 devices using code WINNER and ship to Atlantis. What is the final total?
```

- Quan sat:
  - MiMo raw output tu viet `Observation` voi gia/stock/weight sai.
  - Real tool result tra gia/stock/weight dung.
  - `calc_shipping` tra `UNSUPPORTED_DESTINATION`.
  - Final answer an toan: khong tinh final total vi Atlantis khong duoc support.

- RCA:
  - Agent v1 text parser van de bi nhiem boi model-written Observation.
  - Agent v2 can parse stricter, reject model-written Observation, validate arguments, va retry khi output tron Action/Observation/Final Answer.

Checks sau Phase 4:

```text
Trace files created: yes
git check-ignore .env -> .env
git grep -n "tp\\-" -> no tracked matches
git grep -n "sk\\-" -> no tracked matches
```

## Tiep theo: Phase 5

Phase tiep theo la `Agent v2 Robustness va Regression Tests`.

Viec can lam:

- Tao `src/agent/agent_v2.py`.
- Tao/cap nhat parser robust.
- Catch provider exception.
- Retry malformed/provider error.
- Reject hallucinated/unknown tool.
- Validate arguments.
- Detect repeated action.
- Dung fixtures tu failure trace Phase 4 de viet regression tests.

## Phase 5: Agent v2 Robustness va Regression Tests

Da lam:

- Tao `src/agent/parsers.py`.
- Tao `src/agent/agent_v2.py`.
- Cap nhat `main.py` de ho tro `--mode agent-v2`.
- Tao `tests/fixtures/llm_outputs.py`.
- Tao `tests/fixtures/__init__.py`.
- Tao `tests/test_parser.py`.
- Tao `tests/test_agent_v2.py`.
- Luu before/after evidence:
  - `report/evidence/traces/agent_v2_fix_trace.md`

Agent v2 da co:

- Parser strict cho:
  - `Action: tool_name({...})`
  - raw JSON action
  - markdown-fenced JSON action
- Reject model-written `Observation`.
- Reject multiple actions trong mot response.
- Retry parser error toi da 2 lan.
- Catch provider exception.
- Log `PROVIDER_ERROR`.
- Retry provider error toi da 2 lan.
- Graceful fallback khi provider bi rate limit.
- Validate unknown tool.
- Validate missing/unknown arguments.
- Validate argument type/value co ban.
- Detect repeated action khi cung action lap 3 lan.
- Log `REPEATED_ACTION`.
- Luon log `AGENT_END` khi ket thuc co kiem soat.

Regression tests tu failure Phase 4:

- MiMo tu viet `Observation` -> Agent v2 reject va retry.
- MiMo/provider `429 Too many requests` -> Agent v2 retry, fallback, log `AGENT_END`.

Test da chay:

```powershell
pytest tests/test_parser.py tests/test_agent_v2.py tests/test_agent_v1.py tests/test_chatbot.py tests/test_telemetry.py tests/test_provider_factory.py tests/test_tools.py
```

Ket qua:

```text
52 passed
```

Live MiMo Agent v2 da chay:

```powershell
python main.py --mode agent-v2 --provider mimo --prompt "I want to buy 2 iPhone 15 devices using code WINNER and ship to Hanoi. What is the final total?"
```

Ket qua live:

- Step 1 goi duoc `get_product_details`.
- Step 2 gap `RateLimitError 429`.
- Agent v2 retry 2 lan.
- Agent v2 khong crash.
- Agent v2 tra fallback:

```text
I cannot complete the request right now because the model provider is unavailable or rate-limited. Please retry in a moment.
```

- Log ket thuc:

```text
AGENT_END termination_reason=provider_error
```

Ghi chu:

- Live Agent v2 chua tao duoc success trace full order vi MiMo dang rate limit.
- Logic normal va reliability da duoc verify bang mock/unit tests.
- Khi provider het rate limit, can chay lai Agent v2 query demo de tao success trace that cho Phase 6/7.

## Tiep theo: Phase 6

Phase tiep theo la `Deterministic Benchmark, Provider Comparison va Ablation`.

Viec can lam:

- Tao `evaluation/test_cases.json`.
- Tao `evaluation/validators.py`.
- Tao `evaluation/run_benchmark.py`.
- Tao `evaluation/analyze_results.py`.
- Tao `config/pricing.json`.
- Chay benchmark chinh bang MiMo khi provider on dinh.
- Truoc submission, can co secondary provider that cho 5 representative cases.

## Phase 6: Deterministic Benchmark, Provider Comparison va Ablation

Da lam:

- Tao `config/pricing.json`.
- Tao `evaluation/test_cases.json` voi 20 business cases.
- Tao `evaluation/validators.py`.
- Tao `evaluation/run_benchmark.py`.
- Tao `evaluation/analyze_results.py`.
- Tao `evaluation/configs/tool_specs_v1.json`.
- Tao `evaluation/configs/tool_specs_v2.json`.
- Tao `evaluation/configs/prompt_v1.txt`.
- Tao `evaluation/configs/prompt_v2.txt`.
- Tao `evaluation/results/benchmark_results.csv`.
- Tao `evaluation/results/summary.md`.
- Tao `evaluation/results/provider_comparison.csv`.
- Tao `evaluation/results/provider_comparison.md`.
- Tao `evaluation/results/ablation_results.csv`.
- Tao `evaluation/results/ablation_summary.md`.
- Tao `tests/test_evaluation.py`.

Evaluation strategy da dung:

- Business benchmark tach rieng reliability tests.
- Success rate dung deterministic validators.
- Khong dung LLM-as-a-judge.
- Full-order validator kiem tra `final_total_vnd` tu answer hoac `calculate_order_total` tool result.
- Tool sequence validator kiem tra required/forbidden tools.
- Summary co token, latency, parser errors, retries, provider errors.

Business cases hien co:

- simple Q&A;
- product details;
- stock available;
- insufficient stock;
- active coupon;
- expired coupon;
- unknown coupon;
- shipping Hanoi;
- shipping Ho Chi Minh City;
- unsupported city;
- full order with valid coupon;
- full order without coupon;
- invalid quantity;
- invalid weight;
- search products;
- empty search;
- Laptop Air detail;
- Wireless Headphones full order;
- Laptop insufficient stock;
- Da Nang shipping.

Smoke benchmark da chay:

```powershell
python evaluation/run_benchmark.py --provider mimo --mode chatbot --case-id B01 --output evaluation/results/benchmark_results.csv
python evaluation/analyze_results.py --input evaluation/results/benchmark_results.csv --output evaluation/results/summary.md
```

Ket qua smoke:

```text
chatbot + mimo
cases: 1
passed: 1
success rate: 100%
total tokens: 649
latency: 12114 ms
```

Provider comparison development run:

```powershell
python evaluation/run_benchmark.py --provider gemini --mode agent-v2 --limit 5 --output evaluation/results/provider_comparison.csv
python evaluation/analyze_results.py --input evaluation/results/provider_comparison.csv --output evaluation/results/provider_comparison.md
```

Ket qua:

- Gemini chua co `GEMINI_API_KEY`.
- Script khong crash.
- 5 rows duoc mark `skipped`.
- Truoc submission van can chay that it nhat 5 representative cases bang Gemini hoac OpenAI.

Ablation:

- Configs da tao.
- `ablation_results.csv` va `ablation_summary.md` dang de status `pending`.
- Chua chay ablation that de tranh tang live API calls khi MiMo vua bi rate limit.

Tests sau Phase 6:

```powershell
pytest tests/test_evaluation.py tests/test_parser.py tests/test_agent_v2.py tests/test_agent_v1.py tests/test_chatbot.py tests/test_telemetry.py tests/test_provider_factory.py tests/test_tools.py
```

Ket qua:

```text
56 passed
```

Secret checks sau Phase 6:

```text
git check-ignore .env -> .env
git grep -n "tp\\-" -> no tracked matches
git grep -n "sk\\-" -> no tracked matches
```

Can lam truoc submission:

- Chay benchmark MiMo day du hon khi rate limit on dinh:

```powershell
python evaluation/run_benchmark.py --provider mimo --mode all --output evaluation/results/benchmark_results.csv
python evaluation/analyze_results.py
```

- Cau hinh Gemini hoac OpenAI key trong `.env`.
- Chay provider comparison that:

```powershell
python evaluation/run_benchmark.py --provider gemini --mode agent-v2 --limit 5 --output evaluation/results/provider_comparison.csv
python evaluation/analyze_results.py --input evaluation/results/provider_comparison.csv --output evaluation/results/provider_comparison.md
```

Neu khong co Gemini thi dung:

```powershell
python evaluation/run_benchmark.py --provider openai --mode agent-v2 --limit 5 --output evaluation/results/provider_comparison.csv
python evaluation/analyze_results.py --input evaluation/results/provider_comparison.csv --output evaluation/results/provider_comparison.md
```

Provider comparison thuc te da hoan thanh sau khi cau hinh Gemini:

- `GEMINI_MODEL` da doi sang `gemini-3.1-flash-lite` vi `gemini-1.5-flash` khong con ho tro va `gemini-2.5-flash` cham free-tier quota.
- Da chay 5 representative cases bang `agent-v2 + gemini`.
- Cases:
  - `B02` product details;
  - `B03` stock;
  - `B05` coupon;
  - `B08` shipping Hanoi;
  - `B15` search products.
- Command da chay:

```powershell
python evaluation/run_benchmark.py --provider gemini --mode agent-v2 --case-ids B02,B03,B05,B08,B15 --request-delay 15 --agent-max-retries 0 --output evaluation/results/provider_comparison.csv --append
python evaluation/analyze_results.py --input evaluation/results/provider_comparison.csv --output evaluation/results/provider_comparison.md
```

- Ket qua:

```text
agent-v2 + gemini
model: gemini-3.1-flash-lite
cases: 5
skipped: 0
passed: 5
success rate: 100%
provider errors: 0
```

- Output:
  - `evaluation/results/provider_comparison.csv`
  - `evaluation/results/provider_comparison.md`

## Tiep theo: Phase 7

Phase tiep theo la `Reports, Diagrams, Secret Scan va Live Demo Rehearsal`.

Viec can lam:

- Tao group report tu template.
- Tao individual report tu template.
- Chen traces Phase 4/5.
- Chen benchmark summary Phase 6.
- Chen flowcharts.
- Update README.
- Rehearse demo.

## Phase 7: Reports, Diagrams, Secret Scan va Live Demo Rehearsal

Da lam:

- Tao group report:
  - `report/group_report/GROUP_REPORT_Solo_Kieu_Duc_Long.md`
- Tao individual report:
  - `report/individual_reports/REPORT_Kieu_Duc_Long.md`
- Cap nhat `README.md` voi:
  - setup `.env`;
  - MiMo quickstart;
  - Gemini provider switching;
  - demo commands;
  - log inspection commands;
  - benchmark commands;
  - evidence/report paths;
  - secret safety commands.
- Group report da co:
  - executive summary;
  - Chatbot flow diagram;
  - ReAct flow diagram;
  - tool inventory;
  - provider list;
  - telemetry dashboard;
  - benchmark smoke;
  - Gemini provider comparison;
  - success trace;
  - failure traces;
  - RCA;
  - Agent v1 -> Agent v2 before/after evidence;
  - production readiness.
- Individual report da co:
  - technical contributions;
  - debugging case study;
  - personal insights;
  - future improvements.

Demo rehearsal da chay:

```powershell
python main.py --mode agent-v2 --provider gemini --prompt "How much is shipping 0.7 kg to Hanoi?"
```

Ket qua:

```text
The shipping fee for 0.7 kg to Hanoi is 37,000 VND.
```

Log co:

```text
AGENT_START
LLM_METRIC
AGENT_STEP
TOOL_CALL calc_shipping
TOOL_RESULT calc_shipping
FINAL_ANSWER
AGENT_END termination_reason=final_answer
```

Final tests:

```powershell
pytest tests/test_evaluation.py tests/test_parser.py tests/test_agent_v2.py tests/test_agent_v1.py tests/test_chatbot.py tests/test_telemetry.py tests/test_provider_factory.py tests/test_tools.py
```

Ket qua:

```text
56 passed
```

Final secret checks:

```text
git check-ignore .env -> .env
git grep -n "tp\\-" -> no tracked matches
git grep -n "sk\\-" -> no tracked matches
```

## Follow-up Audit Fix: Agent v2 Repeated Action Cache

Trong audit cuoi, benchmark `B11` bang MiMo phat hien Agent v2 co the dung qua som vi repeated action:

```text
get_product_details -> check_stock -> get_discount -> calc_shipping -> repeated get_product_details
```

Da sua:

- Agent v2 cache successful observation theo action signature.
- Neu cung action lap lai lan thu 2, Agent v2 khong dung ngay.
- Agent v2 feed cached observation vao prompt va yeu cau model dung observation da co de chon next action.
- Neu van lap tiep thi moi dung bang `REPEATED_ACTION`.

Test moi:

```text
tests/test_agent_v2.py::test_agent_v2_reuses_cached_observation_once_before_stopping
```

Tests sau fix:

```text
57 passed
```

Benchmark `B11` da rerun thanh cong:

```powershell
python evaluation/run_benchmark.py --provider mimo --mode agent-v2 --case-id B11 --request-delay 25 --agent-max-retries 1 --output evaluation/results/benchmark_results.csv
python evaluation/analyze_results.py --input evaluation/results/benchmark_results.csv --output evaluation/results/summary.md
```

Ket qua:

```text
agent-v2 + mimo
case: B11 full_order
passed: 1/1
success rate: 100%
tool sequence: get_product_details -> get_discount -> check_stock -> calc_shipping -> calculate_order_total
final_total_vnd: 36,037,000
provider errors: 0
```
