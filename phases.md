# Phases triển khai Lab 3 Solo

File này là checklist thực thi cho một người làm một nhóm. Mỗi phase nên kết thúc bằng test hoặc log evidence cụ thể trước khi chuyển tiếp.

Flow chính:

```text
Provider Foundation
-> Mock Data và Tools
-> Chatbot Baseline
-> Agent v1
-> Real Failure Trace
-> Agent v2
-> Benchmark và Ablation
-> Reports và Demo
```

## Phase 0: Repository Setup và Provider Foundation

### Mục tiêu

Chuẩn bị nền tảng chạy được provider theo chiến lược MiMo-first, chưa cần gọi API thật cho đến điểm dừng API key.

### Tasks

- [ ] Tạo hoặc cập nhật `.env.example`:
  - `DEFAULT_PROVIDER=mimo`
  - `MIMO_API_KEY=`
  - `MIMO_BASE_URL=https://token-plan-sgp.xiaomimimo.com/v1`
  - `MIMO_MODEL=mimo-v2.5-pro`
  - `GEMINI_API_KEY=`
  - `GEMINI_MODEL=`
  - `OPENAI_API_KEY=`
  - `OPENAI_MODEL=`
  - `LOCAL_MODEL_PATH=`
- [ ] Confirm `.env` nằm trong `.gitignore`.
- [ ] Tạo `src/core/mimo_provider.py`.
- [ ] Tạo `src/core/provider_factory.py`.
- [ ] Factory hỗ trợ `mimo`, `gemini`, `openai`, `local`.
- [ ] Factory chọn provider theo thứ tự:
  - CLI argument;
  - `DEFAULT_PROVIDER`;
  - default hard fallback `mimo`.
- [ ] Missing key phải báo lỗi dễ hiểu:
  - `Missing MIMO_API_KEY in .env`
  - `Missing GEMINI_API_KEY in .env`
  - `Missing OPENAI_API_KEY in .env`
- [ ] Không xóa provider cũ.
- [ ] Không hard-code API key.
- [ ] Tạo `tests/test_provider_factory.py`.
- [ ] Mock OpenAI client khi test `MiMoProvider`.
- [ ] Chạy `git check-ignore .env`.
- [ ] Chạy `git grep -n "tp\\-"`.
- [ ] Chạy `git grep -n "sk\\-"`.
- [ ] Confirm không có API key trong tracked files.
- [ ] Sau khi user tự paste key vào `.env`, chạy một MiMo smoke test riêng.

### Definition of Done

- [ ] `.env` bị Git ignore.
- [ ] Không có secret trong tracked files.
- [ ] Unit test provider factory pass.
- [ ] `MiMoProvider` instantiate được bằng mock.
- [ ] Có thể instantiate provider bằng mock/env giả.
- [ ] Telemetry provider name dự kiến là `mimo`, không phải `openai`.
- [ ] MiMo smoke test chạy được sau khi user tự điền key.

### Commands

```powershell
pytest tests/test_provider_factory.py
git check-ignore .env
git grep -n "tp\\-"
git grep -n "sk\\-"
```

### Điểm dừng API key

Sau khi phase này xong và trước khi chạy live MiMo call đầu tiên, dừng lại và nhắc:

```text
Vui lòng tạo `.env` từ `.env.example` và paste `MIMO_API_KEY` vào `.env`. Không gửi API key trong chat.
```

## Phase 1: Mock Data, Core Tools và Tool Tests

### Mục tiêu

Tạo deterministic local dataset và các e-commerce tools để agent không phải bịa thông tin. Làm 3 core tools trước để có MVP nhanh, sau đó hoàn thiện supporting và bonus tools.

### Tool priority

Core:

- `check_stock`
- `get_discount`
- `calc_shipping`

Supporting:

- `get_product_details`
- `calculate_order_total`

Bonus:

- `search_products`

### Tasks

- [ ] Tạo `data/products.json`.
- [ ] Tạo `data/coupons.json`.
- [ ] Tạo `data/shipping_rates.json`.
- [ ] Tạo `src/tools/ecommerce_tools.py`.
- [ ] Tạo `src/tools/registry.py`.
- [ ] Tạo `src/tools/schemas.py` nếu dùng Pydantic validation.
- [ ] Implement 3 core tools trước:
  - `check_stock`
  - `get_discount`
  - `calc_shipping`
- [ ] Implement supporting tools:
  - `get_product_details`
  - `calculate_order_total`
- [ ] Implement bonus tool sau khi MVP ổn định:
  - `search_products`
- [ ] Chuẩn hóa tool response:

```json
{
  "status": "success",
  "data": {},
  "error": null
}
```

- [ ] Tool trả structured dict, không throw exception khó hiểu với user input bình thường.
- [ ] Invalid item/coupon/city/quantity/weight trả structured error.
- [ ] Tạo `tests/test_tools.py`.

### Definition of Done

- [ ] 3 core tools pass tests trước.
- [ ] Supporting tools pass tests.
- [ ] Bonus tool hoàn thành sau khi core tools ổn định.
- [ ] Invalid input được handle an toàn.
- [ ] Tests pass.

### Commands

```powershell
pytest tests/test_tools.py
```

## Phase 2: Chatbot Baseline, CLI và Telemetry cơ bản

### Mục tiêu

Có baseline chatbot để so sánh với Agent v1/v2.

### Tasks

- [ ] Tạo `src/chatbot.py`.
- [ ] Chatbot gọi LLM đúng một lần.
- [ ] Chatbot không gọi tool.
- [ ] Tạo `tests/test_chatbot.py`.
- [ ] Dùng fake provider để test chatbot.
- [ ] Verify chatbot chỉ gọi LLM đúng một lần.
- [ ] Log:
  - `CHATBOT_START`
  - `LLM_METRIC`
  - `CHATBOT_END`
- [ ] Tạo `tests/test_telemetry.py`.
- [ ] Test `LLM_METRIC` có provider/model/token/latency.
- [ ] Test MiMo log là `mimo`, không phải `openai`.
- [ ] Test API key không xuất hiện trong log.
- [ ] Tạo `main.py`.
- [ ] CLI hỗ trợ:
  - `--mode chatbot`
  - `--provider mimo`
  - `--interactive`
- [ ] CLI handle missing API key bằng message rõ ràng.

### Definition of Done

- [ ] `tests/test_chatbot.py` pass.
- [ ] `tests/test_telemetry.py` pass.
- [ ] `python main.py --mode chatbot --provider mimo` chạy được khi có key.
- [ ] Log có provider/model/token/latency.
- [ ] Chatbot limitation được ghi lại bằng ít nhất một example.

### Commands

```powershell
pytest tests/test_chatbot.py tests/test_telemetry.py
python main.py --mode chatbot --provider mimo
Get-Content logs\*.log -Tail 20
```

### Ghi chú API key

Nếu chưa có `.env` hoặc thiếu `MIMO_API_KEY`, dừng lại và nhắc bạn paste key vào `.env`. Không yêu cầu gửi key trong chat.

## Phase 3: Agent v1 ReAct Loop

### Mục tiêu

Hoàn thiện Agent v1 đủ để gọi tool, append observation và trả final answer cho workflow chuẩn.

### Tasks

- [ ] Implement `src/agent/agent.py`.
- [ ] System prompt liệt kê tools và format.
- [ ] Detect `Final Answer`.
- [ ] Parse `Action: tool_name({...})`.
- [ ] Execute tool từ registry.
- [ ] Append `Observation` vào prompt.
- [ ] Enforce `max_steps`.
- [ ] Tạo `tests/test_agent_v1.py`.
- [ ] Tạo scripted fake provider cho Agent v1.
- [ ] Test direct `Final Answer`.
- [ ] Test một valid `Action`.
- [ ] Test `Action -> Observation -> next LLM prompt`.
- [ ] Verify observation xuất hiện trong prompt tiếp theo.
- [ ] Test unknown tool.
- [ ] Test `max_steps`.
- [ ] Log:
  - `AGENT_START`
  - `AGENT_STEP`
  - `TOOL_CALL`
  - `TOOL_RESULT`
  - `FINAL_ANSWER`
  - `MAX_STEPS_EXCEEDED`
  - `AGENT_END`
- [ ] CLI hỗ trợ `--mode agent-v1`.

### Definition of Done

- [ ] Unit tests Agent v1 pass trước khi chạy API thật.
- [ ] Agent v1 giải được query mua 2 iPhone 15 + WINNER + Hanoi.
- [ ] Agent v1 gọi ít nhất 2 tools trong một run.
- [ ] Observation xuất hiện trong prompt/history hoặc trace.
- [ ] Có log đủ để phân tích.

### Commands

```powershell
pytest tests/test_agent_v1.py
python main.py --mode agent-v1 --provider mimo
Get-Content logs\*.log -Tail 80
```

## Phase 4: Run MiMo Agent v1, Capture Real Traces và Perform RCA

### Mục tiêu

Chạy Agent v1 bằng MiMo API thật để tạo evidence: success trace thật, failure trace thật và root-cause analysis.

### Tasks

- [ ] Chạy success query:

```text
I want to buy 2 iPhone 15 devices using code WINNER and ship to Hanoi. What is the final total?
```

- [ ] Đọc log sau khi chạy.
- [ ] Lưu `report/evidence/traces/success_trace_multi_step.md`.
- [ ] Cố tình chạy failure-oriented queries bằng input tự nhiên:
  - unsupported city `Atlantis`;
  - coupon `FAKECODE`;
  - buy `100 iPhone 15`;
  - query thiếu thông tin cần thiết;
  - query mơ hồ dễ làm agent gọi sai tool hoặc truyền sai arguments.
- [ ] Chọn ít nhất một failure thật của Agent v1.
- [ ] Nếu lỗi thật không phải parser error, giữ nguyên lỗi thực tế để làm case study.
- [ ] Lưu failure trace, ví dụ:
  - `failure_trace_parser_error.md`
  - `failure_trace_unknown_tool.md`
  - `failure_trace_repeated_action.md`
  - hoặc file failure thật khác.
- [ ] Lưu raw LLM output.
- [ ] Lưu full tool action.
- [ ] Lưu observation.
- [ ] Lưu log snippet.
- [ ] Không dựng trace giả.
- [ ] Chọn lỗi thật có thể sửa trong Agent v2.
- [ ] Ghi rõ:
  - input;
  - raw LLM output;
  - action;
  - observation;
  - failure symptom;
  - root cause;
  - planned fix;
  - log snippet.

### Definition of Done

- [ ] Có ít nhất 1 success trace thật từ MiMo.
- [ ] Có ít nhất 1 failure trace thật từ MiMo.
- [ ] RCA ghi rõ symptom, root cause và planned fix.
- [ ] Failure trace có log snippet đủ dùng trong report.

### Commands

```powershell
python main.py --mode agent-v1 --provider mimo
Get-Content logs\*.log -Tail 120
```

## Phase 5: Agent v2 Robustness và Regression Tests

### Mục tiêu

Agent v2 phải cải thiện dựa trên lỗi đã thấy ở Agent v1, không chỉ prompt engineering mơ hồ. Mock regression tests dùng để tái lập lỗi deterministic; trace thật vẫn lấy từ MiMo.

### Tasks

- [ ] Tạo `src/agent/agent_v2.py`.
- [ ] Tạo hoặc cập nhật `src/agent/parsers.py`.
- [ ] Parser v2 hỗ trợ:
  - raw JSON;
  - JSON trong markdown fence;
  - whitespace dư;
  - malformed action;
  - empty action name.
- [ ] Validate unknown tool.
- [ ] Validate argument keys/types.
- [ ] Retry malformed LLM output tối đa 2 lần.
- [ ] Parser feedback được thêm vào prompt retry.
- [ ] Detect repeated action.
- [ ] Stop khi cùng action lặp 3 lần.
- [ ] Return fallback answer rõ ràng khi không thể hoàn tất.
- [ ] Tạo `tests/fixtures/llm_outputs.py`.
- [ ] Tạo `tests/test_agent_v2.py`.
- [ ] Dùng mock fixture để tái lập lỗi v1.
- [ ] Chạy cùng fixture trên Agent v2.
- [ ] Lưu before/after evidence.
- [ ] Test markdown-fenced JSON.
- [ ] Test malformed JSON.
- [ ] Test unknown tool.
- [ ] Test wrong argument type.
- [ ] Test missing argument.
- [ ] Test repeated action.
- [ ] Test empty observation.
- [ ] Test provider exception.
- [ ] Log:
  - `PARSER_ERROR`
  - `UNKNOWN_TOOL`
  - `INVALID_ARGUMENTS`
  - `RETRY`
  - `REPEATED_ACTION`
  - termination reason.
- [ ] CLI hỗ trợ `--mode agent-v2`.

### Definition of Done

- [ ] Regression test tái lập được lỗi Agent v1.
- [ ] Agent v2 fix hoặc mitigate được lỗi đó.
- [ ] Agent v2 giải được normal complete-order query.
- [ ] Có before/after evidence.
- [ ] Logs thể hiện retry/error/termination reason khi có lỗi.

### Commands

```powershell
pytest tests/test_parser.py tests/test_agent_v2.py
python main.py --mode agent-v2 --provider mimo
Get-Content logs\*.log -Tail 120
```

## Phase 6: Deterministic Benchmark, Provider Comparison và Ablation

### Mục tiêu

Tạo kết quả định lượng đáng tin cậy để điền group report và scoring. Business benchmark chạy bằng API thật; reliability tests chạy bằng mock provider.

### Tasks

- [ ] Tạo `evaluation/test_cases.json` với ít nhất 20 cases.
- [ ] Mỗi test case có `expected` và `validator`.
- [ ] Tạo `evaluation/validators.py`.
- [ ] Không dùng LLM tự chấm câu trả lời.
- [ ] Tách business benchmark khỏi reliability tests.
- [ ] Tạo `evaluation/run_benchmark.py`.
- [ ] Tạo `evaluation/analyze_results.py`.
- [ ] Tạo `config/pricing.json`.
- [ ] Với MiMo Token Plan, dùng `cost_estimate=null` nếu chưa có pricing chính xác.
- [ ] Benchmark chính chạy:
  - `chatbot + mimo`
  - `agent-v1 + mimo`
  - `agent-v2 + mimo`
- [ ] Benchmark phụ trong development:
  - ưu tiên `agent-v2 + gemini`;
  - fallback `agent-v2 + openai`;
  - skip rõ nếu thiếu API key.
- [ ] Trước submission, chạy ít nhất 5 case bằng Gemini hoặc OpenAI.
- [ ] Export:
  - `evaluation/results/benchmark_results.csv`
  - `evaluation/results/summary.md`
- [ ] Tạo `evaluation/results/provider_comparison.csv`.
- [ ] Tạo `evaluation/results/provider_comparison.md`.
- [ ] Tạo `evaluation/configs/tool_specs_v1.json`.
- [ ] Tạo `evaluation/configs/tool_specs_v2.json`.
- [ ] Tạo `evaluation/configs/prompt_v1.txt`.
- [ ] Tạo `evaluation/configs/prompt_v2.txt`.
- [ ] Chạy ablation subset từ 5 đến 10 cases.
- [ ] Tạo `evaluation/results/ablation_results.csv`.
- [ ] Tạo `evaluation/results/ablation_summary.md`.
- [ ] Summary có comparison table:
  - total cases;
  - correct responses;
  - success rate;
  - average latency;
  - average tokens;
  - parser errors;
  - retry count;
  - estimated cost hoặc cost note.

### Definition of Done

- [ ] Business benchmark dùng deterministic validators.
- [ ] Không dùng LLM-as-a-judge để tính success rate.
- [ ] CSV được tạo.
- [ ] Markdown summary được tạo.
- [ ] Provider comparison có MiMo và provider phụ thật trước submission.
- [ ] Ablation results được export.

### Commands

```powershell
python evaluation/run_benchmark.py --provider mimo
python evaluation/analyze_results.py
Get-Content evaluation\results\summary.md
Get-Content evaluation\results\provider_comparison.md
Get-Content evaluation\results\ablation_summary.md
```

## Phase 7: Reports, Diagrams, Secret Scan và Live Demo Rehearsal

### Mục tiêu

Đóng gói evidence thành submission-ready deliverables, kiểm tra secret safety và rehearsal demo thật.

### Tasks

- [ ] Tạo group report từ template:

```text
report/group_report/GROUP_REPORT_[Team Name].md
```

- [ ] Tạo individual report từ template:

```text
report/individual_reports/REPORT_[Your Name].md
```

- [ ] Thêm Chatbot flow diagram.
- [ ] Thêm ReAct flow diagram.
- [ ] Thêm tool inventory.
- [ ] Thêm telemetry metrics.
- [ ] Chèn deterministic benchmark table.
- [ ] Chèn provider comparison table.
- [ ] Chèn ablation table.
- [ ] Chèn success trace thật.
- [ ] Chèn failure trace thật.
- [ ] Chèn Agent v1 -> Agent v2 before/after evidence.
- [ ] Thêm failure trace + RCA.
- [ ] Thêm ablation experiments.
- [ ] Update README:
  - MiMo quickstart;
  - provider switching;
  - test commands;
  - benchmark commands;
  - log inspection;
  - demo script.
- [ ] Chạy secret scan trước commit cuối.
- [ ] Cấu hình ít nhất một secondary provider trước submission.
- [ ] Rehearse switching demo MiMo -> Gemini hoặc MiMo -> OpenAI.
- [ ] Rehearse live demo từ terminal sạch.

### Definition of Done

- [ ] Group report đầy đủ rubric.
- [ ] Individual report đầy đủ 40 điểm.
- [ ] README đủ để người khác reproduce.
- [ ] Demo query chạy ổn bằng MiMo.
- [ ] Provider switching demo chạy thật trước submission.
- [ ] Logs và benchmark evidence đã lưu.
- [ ] Secret scan không phát hiện key trong tracked files.

### Commands

```powershell
git status
git check-ignore .env
git grep -n "tp\\-"
git grep -n "sk\\-"

python main.py --mode chatbot --provider mimo
python main.py --mode agent-v1 --provider mimo
python main.py --mode agent-v2 --provider mimo
python main.py --mode agent-v2 --provider gemini
python evaluation/run_benchmark.py --provider mimo
```

Nếu Gemini chưa cấu hình nhưng OpenAI có key:

```powershell
python main.py --mode agent-v2 --provider openai
```

## Final Checklist

- [ ] Chatbot baseline works.
- [ ] Agent v1 uses ReAct loop.
- [ ] Agent v1 calls at least two tools.
- [ ] Six e-commerce tools are available.
- [ ] Observations feed back into the prompt.
- [ ] Agent v1 failure trace is saved.
- [ ] Agent v2 fixes documented v1 failure.
- [ ] `max_steps` guardrail works.
- [ ] Repeated actions are detected.
- [ ] Invalid tools are rejected.
- [ ] Invalid arguments are rejected.
- [ ] Markdown-fenced JSON can be parsed.
- [ ] Retry logic works.
- [ ] Structured logs are generated.
- [ ] Token usage is tracked.
- [ ] Latency is tracked.
- [ ] Estimated cost is tracked with policy.
- [ ] Benchmark CSV is generated.
- [ ] Chatbot, Agent v1 and Agent v2 are compared.
- [ ] MiMo và ít nhất một secondary provider đã được so sánh thật trước submission.
- [ ] Business benchmark dùng deterministic validators.
- [ ] Không dùng LLM-as-a-judge để tính success rate.
- [ ] Reliability tests dùng mock provider.
- [ ] Có `tests/test_chatbot.py`.
- [ ] Có `tests/test_agent_v1.py`.
- [ ] Có `tests/test_agent_v2.py`.
- [ ] Có `tests/test_telemetry.py`.
- [ ] Có `evaluation/validators.py`.
- [ ] Có failure trace thật từ MiMo.
- [ ] Không dựng log giả.
- [ ] Có provider comparison thật trước submission.
- [ ] Có ablation results.
- [ ] MiMo Token Plan không bị ghi cost sai thành `0.0`.
- [ ] `.env` bị Git ignore.
- [ ] Không có key dạng `tp\-...` hoặc `sk\-...` trong tracked files.
- [ ] Ablation experiments are documented.
- [ ] Automated tests pass.
- [ ] README is complete.
- [ ] Flowcharts are included.
- [ ] Group report is complete.
- [ ] Individual report is complete.
- [ ] Live demo has been rehearsed.
