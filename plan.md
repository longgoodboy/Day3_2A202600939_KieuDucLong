# Kế hoạch Lab 3 Solo: Chatbot vs ReAct Agent

- **Team Name**: `Solo - Kiều Đức Long`
- **Student Name**: `Kiều Đức Long`
- **Student ID**: `2A202600939`
- **Mục tiêu điểm**: 60/60 group score + 40/40 individual score
- **Primary provider**: Xiaomi MiMo (`mimo-v2.5-pro`)

## 1. Mục tiêu tổng thể

Lab này xây dựng một Smart E-commerce Assistant dạng CLI để so sánh ba hệ thống:

1. **Baseline Chatbot**: trả lời bằng một LLM call, không dùng tool.
2. **ReAct Agent v1**: dùng vòng lặp `Thought -> Action -> Observation`, parser đơn giản, đủ để chạy workflow chuẩn và tạo failure trace thật.
3. **ReAct Agent v2**: cải thiện từ lỗi đã quan sát trong log của Agent v1, có parser chắc hơn, retry, validation và guardrail.

Kết quả cuối cùng phải chứng minh được:

- Chatbot nhanh hơn cho câu hỏi đơn giản nhưng dễ hallucinate ở task nhiều bước.
- Agent v1 biết gọi tool và feed observation vào prompt kế tiếp.
- Agent v1 có ít nhất một failure trace thật, đọc được từ structured logs.
- Agent v2 sửa hoặc giảm thiểu lỗi đã thấy ở Agent v1.
- Benchmark dùng deterministic validators, không dùng LLM tự chấm.
- Demo live chạy ổn định bằng MiMo và có provider switching thật trước submission.

## 2. Current State của repo

Repo hiện tại là starter skeleton:

- Có `README.md`, `INSTRUCTOR_GUIDE.md`, `SCORING.md`, `EVALUATION.md`.
- Có provider interface và provider cơ bản trong `src/core/`.
- Có telemetry cơ bản trong `src/telemetry/logger.py` và `src/telemetry/metrics.py`.
- Có `src/agent/agent.py` nhưng ReAct loop còn TODO.
- Chưa có `main.py`.
- Chưa có `src/tools/`.
- Chatbot baseline dùng `src/chatbot.py` để khớp cấu trúc submission.
- Chưa có `evaluation/`.
- Chưa có `src/core/provider_factory.py`.
- Chưa có `src/core/mimo_provider.py`.
- `.env` và `logs/` đã nằm trong `.gitignore`.

Vì vậy implementation nên đi theo hướng nhỏ, rõ, có test từng phần, tránh sửa rộng ngay từ đầu.

## 3. Scoring Strategy

### Group score: target 45/45 base

| Rubric category | Evidence cần tạo | Target |
| --- | --- | ---: |
| Chatbot Baseline | `Chatbot` class, CLI mode, log LLM metric | 2/2 |
| Agent v1 | ReAct loop, 2+ tools, dùng observation | 7/7 |
| Agent v2 | Fix dựa trên failure trace từ v1 | 7/7 |
| Tool Design Evolution | Tool spec v1 vague vs v2 strict | 4/4 |
| Trace Quality | Success trace + failure trace + RCA | 9/9 |
| Evaluation & Analysis | deterministic benchmark, CSV, summary, comparison | 7/7 |
| Flowchart & Insight | Chatbot flow + ReAct flow + lessons | 5/5 |
| Code Quality | Modular code, tests, `.env`, README | 4/4 |

### Bonus: target +15/15

| Bonus category | Planned evidence | Target |
| --- | --- | ---: |
| Extra Monitoring | cost policy, token ratio, P50/P95 latency, retries | +3 |
| Extra Tools | 6 e-commerce tools, search + total calculator | +2 |
| Failure Handling | parser recovery, retry, validation, repeated-action guardrail | +3 |
| Live System Demo | stable MiMo demo + secondary provider switching | +5 |
| Ablation Experiments | prompt format + tool description experiments | +2 |

### Individual score: target 40/40

Vì làm solo, report cá nhân sẽ ghi bạn sở hữu toàn bộ hệ thống, nhưng cần chọn một debugging case study thật để phân tích sâu.

Recommended individual case study:

- Agent v1 lỗi parser khi LLM trả action trong markdown fence hoặc format lệch.
- Nếu MiMo không tạo parser error thật, dùng lỗi thật khác như wrong arguments, unknown tool, repeated action, empty observation, unsupported destination hoặc insufficient stock.
- Root cause phải dựa trên log thật, không dựng log giả.
- Fix phải được chứng minh bằng Agent v2 chạy lại cùng input.

## 4. Provider Strategy

### Primary provider: MiMo

MiMo là provider chính cho:

- chatbot baseline;
- Agent v1;
- Agent v2;
- success trace;
- failure trace;
- business benchmark chính;
- live demo.

`.env` target:

```env
DEFAULT_PROVIDER=mimo
MIMO_API_KEY=
MIMO_BASE_URL=https://token-plan-sgp.xiaomimimo.com/v1
MIMO_MODEL=mimo-v2.5-pro
```

MiMo dùng OpenAI-compatible API protocol nhưng telemetry phải ghi provider là `mimo`, không ghi nhầm thành `openai`.

### Secondary provider: Gemini hoặc OpenAI

Mục đích là chứng minh provider switching:

- Ưu tiên Gemini nếu có `GEMINI_API_KEY`.
- Nếu không có Gemini nhưng có `OPENAI_API_KEY`, dùng OpenAI.
- Development có thể skip provider phụ nếu chưa có key.
- Trước submission phải cấu hình ít nhất một provider phụ và chạy ít nhất 5 representative cases.
- Nếu thiếu API key phụ trong development, benchmark phải skip rõ ràng:

```text
Skipped secondary provider benchmark: API key is not configured.
```

### Optional provider: local

Local GGUF provider giữ lại như fallback/demo optional. Không xóa provider cũ.

## 5. Kiến trúc dự kiến

```text
.
├── main.py
├── config/
│   └── pricing.json
├── data/
│   ├── products.json
│   ├── coupons.json
│   └── shipping_rates.json
├── src/
│   ├── agent/
│   │   ├── agent.py
│   │   ├── agent_v2.py
│   │   └── parsers.py
│   ├── chatbot/
│   │   └── chatbot.py
│   ├── core/
│   │   ├── provider_factory.py
│   │   ├── mimo_provider.py
│   │   ├── openai_provider.py
│   │   ├── gemini_provider.py
│   │   ├── local_provider.py
│   │   └── llm_provider.py
│   ├── tools/
│   │   ├── registry.py
│   │   ├── schemas.py
│   │   └── ecommerce_tools.py
│   └── telemetry/
│       ├── logger.py
│       └── metrics.py
├── evaluation/
│   ├── validators.py
│   ├── test_cases.json
│   ├── run_benchmark.py
│   ├── analyze_results.py
│   ├── configs/
│   └── results/
├── report/
│   ├── evidence/
│   │   ├── traces/
│   │   └── benchmark/
│   ├── group_report/
│   └── individual_reports/
└── tests/
    └── fixtures/
```

## 6. Tool Inventory

Implement tối thiểu 6 tool cho Smart E-commerce Assistant:

| Tool | Purpose | Important behavior |
| --- | --- | --- |
| `search_products` | Tìm sản phẩm theo query/category/max price | Empty result phải an toàn |
| `get_product_details` | Lấy price, weight, category, normalized name | Không để agent tự bịa giá/cân nặng |
| `check_stock` | Kiểm tra tồn kho và requested quantity | Unknown item trả structured error |
| `get_discount` | Kiểm tra coupon active/expired/unknown | Invalid coupon không được silent discount |
| `calc_shipping` | Tính phí ship theo weight + destination | Unsupported city trả clear error |
| `calculate_order_total` | Tính subtotal, discount, shipping, final total | Có breakdown minh bạch |

Tool response nên thống nhất:

```json
{
  "status": "success",
  "data": {},
  "error": null
}
```

Tool v1 có thể dùng description ngắn hơn để phục vụ ablation. Tool v2 phải có description strict, gồm required args, type, supported values và error cases.

## 7. Core Scope vs Bonus Scope

Để tránh quá tải khi làm solo và deadline gần, tools được chia thành ba nhóm:

### Core tools - bắt buộc hoàn thành trước

- `check_stock`
- `get_discount`
- `calc_shipping`

### Supporting tools - nên hoàn thành sau core tools

- `get_product_details`
- `calculate_order_total`

### Bonus tool - làm sau khi MVP ổn định

- `search_products`

Agent v1 chỉ cần gọi ít nhất 2 tools trong một run để đạt yêu cầu cơ bản. Agent v2 và benchmark nâng cao có thể sử dụng đủ 6 tools. Dù `search_products` là bonus theo thứ tự triển khai MVP, vẫn nên hoàn thành trước submission nếu muốn đạt full score/bonus.

## 8. Agent Strategy

### Chatbot baseline

- Gọi LLM đúng một lần.
- Không gọi tool.
- Log `CHATBOT_START`, `LLM_METRIC`, `CHATBOT_END`.
- Dùng fake provider trong unit test để verify chỉ gọi LLM một lần.
- Dùng cùng business test suite với agent để so sánh.

### Agent v1

- Implement trong `src/agent/agent.py`.
- Prompt format:

```text
Thought: ...
Action: tool_name({"arg": "value"})
Observation: ...
Final Answer: ...
```

- Parser v1 có thể đơn giản bằng regex.
- Cần xử lý:
  - Detect `Final Answer`.
  - Parse `Action`.
  - Execute registered tool.
  - Append `Observation` vào prompt.
  - Stop theo `max_steps`.
- Unit tests dùng scripted fake provider trước khi chạy API thật.
- Mục tiêu: solve normal complete-order task và tạo ít nhất một failure trace thật bằng MiMo.

### Agent v2

- Implement trong `src/agent/agent_v2.py`.
- Cải thiện dựa trên log thật của v1.
- Required improvements:
  - Extract JSON từ raw text hoặc markdown fence.
  - Reject unknown tool.
  - Validate argument keys/types.
  - Retry malformed output tối đa 2 lần.
  - Detect repeated action, stop khi cùng action lặp 3 lần.
  - Log termination reason.
  - Trả fallback answer có ích khi không thể hoàn tất order.
- Regression tests dùng mock fixtures để tái lập lỗi v1 deterministic.

## 9. Telemetry Strategy

Log JSON phải đủ làm evidence cho report:

```text
SESSION_START
SESSION_END
CHATBOT_START
CHATBOT_END
AGENT_START
AGENT_STEP
LLM_METRIC
TOOL_CALL
TOOL_RESULT
PARSER_ERROR
UNKNOWN_TOOL
INVALID_ARGUMENTS
RETRY
REPEATED_ACTION
MAX_STEPS_EXCEEDED
FINAL_ANSWER
AGENT_END
```

Mỗi `LLM_METRIC` phải có:

```json
{
  "provider": "mimo",
  "model": "mimo-v2.5-pro",
  "prompt_tokens": 0,
  "completion_tokens": 0,
  "total_tokens": 0,
  "latency_ms": 0.0,
  "cost_estimate": null,
  "cost_note": "N/A: token-plan quota"
}
```

Metrics cần aggregate:

- success rate;
- average latency;
- P50/P95 latency;
- total tokens;
- average tokens/task;
- average steps;
- average tool calls;
- parser-error rate;
- retry rate;
- estimated cost hoặc cost note.

## 10. Telemetry Test Requirements

Tạo:

```text
tests/test_telemetry.py
```

Test tối thiểu:

- [ ] `LLM_METRIC` có provider, model, token usage và latency.
- [ ] `TOOL_CALL` có tool name và arguments.
- [ ] `TOOL_RESULT` có status và result.
- [ ] `AGENT_END` có termination reason.
- [ ] `PARSER_ERROR` được ghi khi parser lỗi.
- [ ] `RETRY` được ghi khi Agent v2 retry.
- [ ] MiMo được log là `mimo`, không phải `openai`.
- [ ] API key không xuất hiện trong logs.

## 11. Pricing and Cost Estimate Policy

Không ghi mặc định `"cost_estimate": 0.0` cho MiMo Token Plan vì dễ gây hiểu nhầm là chi phí bằng 0.

Tạo:

```text
config/pricing.json
```

Ví dụ:

```json
{
  "mimo-v2.5-pro": {
    "input_cost_per_1m_tokens": null,
    "output_cost_per_1m_tokens": null,
    "note": "Token-plan quota; monetary pricing is not configured."
  }
}
```

Nếu chưa có pricing chính xác áp dụng cho Token Plan, telemetry trả:

```json
{
  "cost_estimate": null,
  "cost_note": "N/A: token-plan quota"
}
```

Vẫn phải track token usage đầy đủ. Không tự đặt giá hoặc ghi `0.0` như thể chi phí bằng 0.

## 12. Evaluation Strategy

Tạo `evaluation/test_cases.json` với ít nhất 14 business cases chạy bằng API thật:

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
- empty search.

Các case business benchmark dùng để so sánh:

- chatbot + MiMo;
- Agent v1 + MiMo;
- Agent v2 + MiMo;
- Agent v2 + secondary provider.

Các lỗi kỹ thuật như malformed JSON, markdown-fenced JSON, hallucinated tool, repeated action, empty observation và provider exception không nằm trong business benchmark. Các lỗi này phải được kiểm tra riêng bằng mock provider trong reliability tests.

Output chính:

```text
evaluation/results/benchmark_results.csv
evaluation/results/summary.md
```

## 13. Deterministic Evaluation Strategy

Benchmark không được dùng LLM tự chấm câu trả lời.

Tạo:

```text
evaluation/validators.py
```

Mỗi test case trong `evaluation/test_cases.json` phải có:

- `id`
- `category`
- `query`
- `expected`
- `validator`
- `required_tools` nếu áp dụng
- `forbidden_tools` nếu áp dụng

Ví dụ:

```json
{
  "id": "T09",
  "category": "full_order",
  "query": "I want to buy 2 iPhone 15 devices using WINNER and ship to Hanoi. What is the final total?",
  "expected": {
    "product_name": "iPhone 15",
    "quantity": 2,
    "subtotal_vnd": 40000000,
    "discount_percent": 10,
    "shipping_fee_vnd": 37000,
    "final_total_vnd": 36037000
  },
  "validator": "order_total",
  "required_tools": [
    "check_stock",
    "get_discount",
    "calc_shipping"
  ]
}
```

Required validators:

- `validate_contains_keywords(...)`
- `validate_structured_order_total(...)`
- `validate_tool_sequence(...)`
- `validate_error_handling(...)`
- `validate_no_tool_call(...)`

Success rate phải được tính bằng deterministic validators, không dùng LLM-as-a-judge. Đối với task nhiều bước, kiểm tra cả final answer và tool sequence.

## 14. Business Benchmark vs Reliability Tests

### A. Business benchmark - chạy bằng API thật

Các case nghiệp vụ:

- simple Q&A;
- product details;
- stock;
- active coupon;
- expired coupon;
- unknown coupon;
- shipping;
- unsupported city;
- full order;
- insufficient stock;
- search;
- empty search;
- invalid quantity;
- invalid weight.

Các case này dùng để benchmark:

- chatbot + MiMo;
- Agent v1 + MiMo;
- Agent v2 + MiMo;
- Agent v2 + secondary provider.

### B. Reliability tests - chạy bằng mock provider

Các lỗi sau không nên phụ thuộc vào việc LLM thật có vô tình sinh output lỗi hay không:

- markdown-fenced JSON;
- malformed JSON;
- empty action name;
- hallucinated tool;
- wrong argument type;
- missing argument;
- repeated action;
- empty observation;
- provider exception;
- max steps exceeded.

Tạo:

```text
tests/fixtures/llm_outputs.py
tests/test_agent_v1.py
tests/test_agent_v2.py
```

Reliability tests phải dùng scripted fake provider hoặc mock provider để tái lập lỗi deterministic.

## 15. Secondary Provider Requirement

Trong quá trình development:

- nếu thiếu `GEMINI_API_KEY` và `OPENAI_API_KEY`, hệ thống phải skip rõ ràng thay vì crash.

Trước khi nộp bài:

- phải cấu hình ít nhất một provider phụ;
- ưu tiên Gemini;
- fallback OpenAI;
- chạy ít nhất 5 representative test cases;
- lưu kết quả comparison.

Required outputs:

```text
evaluation/results/provider_comparison.csv
evaluation/results/provider_comparison.md
```

Code vẫn phải giữ behavior:

```text
Skipped secondary provider benchmark: API key is not configured.
```

nhưng trạng thái final submission không nên chỉ có skip message.

## 16. Ablation Execution Plan

Tạo:

```text
evaluation/configs/tool_specs_v1.json
evaluation/configs/tool_specs_v2.json
evaluation/configs/prompt_v1.txt
evaluation/configs/prompt_v2.txt
```

Chạy cùng một subset từ 5 đến 10 test cases cho từng configuration.

### Experiment 1: Tool description quality

So sánh:

```text
Tool specs v1: mô tả ngắn, ít constraints
Tool specs v2: mô tả strict, có args, types và error cases
```

### Experiment 2: Prompt format

So sánh:

```text
Prompt v1: free-form Action text
Prompt v2: strict JSON action format + parser feedback
```

Export:

```text
evaluation/results/ablation_results.csv
evaluation/results/ablation_summary.md
```

Metrics:

- success rate;
- parser errors;
- wrong-tool calls;
- retry count;
- average steps;
- average latency;
- average tokens.

## 17. Real Failure Trace Policy

Mock tests chỉ dùng để tạo regression tests đáng tin cậy.

Báo cáo vẫn phải có ít nhất một failure trace thật được ghi lại khi chạy Agent v1 bằng MiMo API.

Yêu cầu:

- lưu raw LLM output;
- lưu tool action;
- lưu observation;
- lưu log snippet;
- ghi rõ failure symptom;
- phân tích root cause;
- ghi fix được áp dụng trong Agent v2;
- chạy lại cùng input để tạo before/after evidence.

Không dựng log giả.

Nếu MiMo không tạo parser error nhưng lại gặp lỗi khác như:

- wrong arguments;
- unknown tool;
- repeated action;
- empty observation;
- unsupported destination handling;
- insufficient stock handling;

thì sử dụng đúng lỗi thật đó làm debugging case study.

## 18. Evidence và Reports

### Group report

Dù làm solo, vẫn tạo group report vì rubric yêu cầu group score.

Recommended output:

```text
report/group_report/GROUP_REPORT_[Team Name].md
```

Nội dung cần có:

- executive summary;
- architecture;
- ReAct flow diagram;
- tool inventory;
- provider list;
- telemetry dashboard;
- deterministic benchmark table;
- provider comparison table;
- ablation table;
- success trace thật;
- failure trace thật;
- RCA;
- Agent v1 -> Agent v2 before/after evidence;
- production readiness.

### Individual report

Recommended output:

```text
report/individual_reports/REPORT_[Your Name].md
```

Nội dung cần có:

- modules implemented;
- code references;
- one debugging case study;
- log snippet;
- root cause;
- fix applied;
- personal reflection;
- future improvements.

### Trace evidence

Store traces under:

```text
report/evidence/traces/
```

Minimum:

- `success_trace_multi_step.md`;
- `failure_trace_parser_error.md` hoặc file failure thật khác;
- `agent_v2_fix_trace.md`.

## 19. Secret Safety

Không commit API key.

Trước commit cuối, chạy:

```powershell
git status
git check-ignore .env
git grep -n "tp\\-"
git grep -n "sk\\-"
```

Acceptance criteria:

- [ ] `.env` bị Git ignore.
- [ ] Không có MiMo key dạng `tp\-...` trong tracked files.
- [ ] Không có OpenAI key dạng `sk\-...` trong tracked files.
- [ ] Không có API key trong README, report, screenshots hoặc logs.

## 20. Demo Script

Stable query:

```text
I want to buy 2 iPhone 15 devices using code WINNER and ship to Hanoi. What is the final total?
```

Demo commands:

```powershell
python main.py --mode chatbot --provider mimo
python main.py --mode agent-v1 --provider mimo
python main.py --mode agent-v2 --provider mimo
python main.py --mode agent-v2 --provider gemini
python main.py --mode agent-v2 --provider openai
python evaluation/run_benchmark.py --provider mimo
```

Nếu Gemini chưa cấu hình nhưng OpenAI có key, dùng OpenAI cho switching demo. Trước submission không nên chỉ có skip message cho provider phụ.

## 21. Priority Levels for Solo Implementation

### P0 - bắt buộc hoàn thành trước

```text
[ ] MiMoProvider
[ ] provider_factory
[ ] `.env.example`
[ ] secret safety
[ ] 3 core tools
[ ] chatbot baseline
[ ] Agent v1 ReAct loop
[ ] observation feedback
[ ] max_steps
[ ] structured logs
[ ] một success trace thật
[ ] một failure trace thật
[ ] Agent v2 sửa failure đó
[ ] deterministic validators cơ bản
[ ] group report
[ ] individual report
```

### P1 - nên hoàn thành để đạt điểm cao

```text
[ ] đủ 6 tools
[ ] retry logic
[ ] repeated-action guardrail
[ ] argument validation
[ ] 20 business benchmark cases
[ ] provider switching thật với Gemini hoặc OpenAI
[ ] P50/P95 latency
[ ] README reproducible
[ ] flowcharts
```

### P2 - làm khi P0 và P1 đã ổn định

```text
[ ] nhiều failure cases hơn
[ ] prompt-format ablation
[ ] tool-description ablation
[ ] config-driven pricing
[ ] local-model fallback demo
[ ] polish CLI output
```

## 22. Definition of Done

Project hoàn thành khi:

- [ ] `.env.example` có MiMo, Gemini, OpenAI, local config.
- [ ] `.env` bị Git ignore và không bị commit.
- [ ] Không có key dạng `tp\-...` hoặc `sk\-...` trong tracked files.
- [ ] `MiMoProvider` hoạt động bằng OpenAI-compatible SDK.
- [ ] `provider_factory.py` chọn provider theo CLI -> `DEFAULT_PROVIDER` -> `mimo`.
- [ ] Chatbot chạy bằng MiMo.
- [ ] Agent v1 chạy bằng MiMo.
- [ ] Agent v2 chạy bằng MiMo.
- [ ] CLI switch provider bằng `--provider`.
- [ ] Agent logic không đổi khi switch provider.
- [ ] 3 core tools pass tests trước; 6 e-commerce tools hoàn thành trước submission.
- [ ] Agent v1 gọi ít nhất 2 tools.
- [ ] Observation được feed lại vào prompt.
- [ ] Agent v1 success trace thật từ MiMo được lưu.
- [ ] Agent v1 failure trace thật từ MiMo được lưu.
- [ ] Không dựng log giả.
- [ ] Agent v2 fix hoặc mitigate failure từ v1.
- [ ] Reliability tests dùng mock provider.
- [ ] Business benchmark dùng deterministic validators.
- [ ] Không dùng LLM-as-a-judge để tính success rate.
- [ ] Structured logs được tạo.
- [ ] Token, latency, step, retry được track.
- [ ] MiMo Token Plan không bị ghi cost sai thành `0.0`.
- [ ] Benchmark CSV và summary được export.
- [ ] Chatbot, Agent v1, Agent v2 được so sánh.
- [ ] MiMo benchmark chính chạy xong.
- [ ] Provider comparison thật chạy ít nhất 5 case trước submission.
- [ ] Ablation experiments được document.
- [ ] Automated tests pass.
- [ ] README hoàn chỉnh.
- [ ] Group report hoàn chỉnh.
- [ ] Individual report hoàn chỉnh.
- [ ] Live demo đã rehearsal.
