# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Le Quoc An
- **Student ID**: 2A202601811
- **Date**: 2026-07-28
- **Provider used for verified run**: Gemini 3.5 Flash
- **Current local configuration**: Phi-3 Mini 4K Instruct Q4 via `llama-cpp-python`

## I. Technical Contribution (15 Points)

### Implemented modules

- `chatbot.py`: a deliberately tool-free chatbot baseline. It uses the common
  provider factory and records one `LLM_METRIC` event per request.
- `src/tools/tools.py`: deterministic e-commerce environment with four tools:
  `check_stock`, `get_discount`, `calc_shipping`, and
  `calculate_order_total`.
- `src/agent/agent.py`: bounded ReAct loop, strict Action JSON parsing,
  tool-argument validation, duplicate-action protection, observation feedback,
  and structured telemetry.
- `src/core/gemini_provider.py`: migrated from the deprecated
  `google-generativeai` package to the supported `google-genai` SDK.
- `run_agent.py`, `evaluate.py`, and `tests/test_agent.py`: reproducible run,
  evaluation, and offline unit-test entry points.

### Local Phi-3 setup status

The local model file `models/Phi-3-mini-4k-instruct-q4.gguf` is present at
`2,393,231,072` bytes. The active `.env` selects `DEFAULT_PROVIDER=local` and
points `LOCAL_MODEL_PATH` to that GGUF file. The provider is loaded lazily, so
the application can switch between Gemini and local Phi-3 without changing
agent code. The local smoke test successfully answered *“Explain what an AI
Agent is in one sentence”*, confirming that Phi-3 and `llama-cpp-python` load
and generate text on this machine.

### Verified implementation evidence

The trace in `logs/2026-07-28.log` shows Agent v2 completing the multi-step
request *“I want to buy 2 iPhones using code WINNER and ship to Hanoi. What is
the total price?”*:

1. `check_stock({"item_name":"iPhone"})` returned stock `10`, unit price
   `25,000,000 VND`, and weight `0.4 kg`.
2. `get_discount({"coupon_code":"WINNER"})` returned `10%`.
3. `calc_shipping({"weight_kg":0.8,"destination":"Hanoi"})` returned
   `36,000 VND`.
4. `calculate_order_total(...)` returned `45,036,000 VND`.
5. The fifth model turn emitted `Final Answer` and the agent terminated with
   status `success`.

## II. Debugging Case Study (10 Points)

### Provider migration and model retirement

**Problem.** Switching temporarily from local Phi-3 to Gemini first produced
`ImportError: cannot import name 'genai' from 'google'`, because the new SDK
was not installed. Once the SDK was installed, the old `gemini-2.5-flash`
model returned `404 NOT_FOUND` because it was unavailable to new users.

**Diagnosis.** The project originally depended on `google-generativeai`, a
deprecated Gemini SDK. Its provider therefore did not match the new
`google-genai` import pattern; in addition, the configured model was no longer
available for this account.

**Solution.** The dependency was changed to `google-genai`,
`GeminiProvider` now creates `genai.Client(api_key=...)`, and `.env` was set
to `DEFAULT_PROVIDER=gemini` and `GEMINI_MODEL=gemini-3.5-flash`.

**Evidence of resolution.** `logs/2026-07-28.log` records a successful Gemini
baseline request followed by the successful five-step ReAct trace. The
baseline call recorded `15,489 ms` latency; the agent trace recorded five
successful `LLM_METRIC` events and `AGENT_END` with status `success`.

### Remaining failure-analysis evidence

This is a real configuration/debugging case, but it is **not yet a failed
ReAct trace**. To satisfy the failure-trace part of the rubric completely, I
must run and preserve one of these cases: invalid coupon `NOTREAL`, unsupported
destination, malformed Action JSON, or repeated identical action. The expected
evidence is an `AGENT_STEP` plus its `TOOL_OBSERVATION` from the log, followed
by a v2 rerun showing the recovery/final answer.

### Phi-3 ReAct failure: multi-action plan accepted as final answer

**Input.** `I want to buy 2 iPhones using code WINNER and ship to Hanoi. What
is the total price?`

**Observed failed trace.** Phi-3 produced several planned actions in its first
response, followed by `Final Answer: ... {total_vnd}`. The old agent checked
for `Final Answer` before parsing the action, so it terminated at step 1 with
the unresolved placeholder `{total_vnd}`. The trace recorded one local request
with `42,991 ms` latency, `853` total tokens, and `AGENT_END` status
`success`; the status was therefore misleading.

**Root cause.** The parser gave `Final Answer` priority over Action and used a
greedy action-regex form. This is especially fragile for smaller local models,
which may emit a full plan instead of exactly one action.

**Fix.** The v2 prompt now explicitly requires exactly one action per response.
The agent parses the first balanced Action JSON object, processes it before any
final-answer text, and accepts a final answer only when no `Action:` is present.
`tests/test_agent.py` now contains a regression case with multiple actions plus
`{total_vnd}` and asserts that the agent continues instead of returning the
placeholder.

**Recovery evidence still required.** Rerun the same Phi-3 request after this
change and paste its successful multi-step trace here. It should call one tool
per turn, then return a numeric VND total after `calculate_order_total`.

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning.** The chatbot makes one direct model call, so it can answer a
   simple factual question but has no way to obtain inventory, coupon, or
   shipping facts. ReAct externalizes progress into a sequence of decisions
   and observations.
2. **Reliability trade-off.** The verified agent answer is grounded because
   its price, discount, shipping, and total each come from an observation.
   However, it used five LLM requests and was therefore slower and more
   failure-prone than a one-call chatbot for simple Q&A.
3. **Observation feedback.** After every tool call, the implementation appends
   JSON observation data to the next prompt. This enabled the verified run to
   compute `0.8 kg` from two `0.4 kg` phones and then use the observed shipping
   result in `calculate_order_total`.

## IV. Future Improvements (5 Points)

- Use Pydantic schemas for tool arguments and structured model output instead
  of parsing text with regex.
- Change `check_stock` to accept `quantity` and deterministically reject orders
  whose requested quantity exceeds stock; the current tool returns stock but
  relies on the model to compare it.
- Maintain a genuine v1 tool-spec list with vague descriptions. At present v1
  and v2 share `get_default_tools()`, so the experiment isolates prompt
  changes but does not yet isolate the claimed tool-description evolution.
- Replace mock cost estimates with provider-specific pricing and add an
  automated summary of P50/P99 latency, tool-call accuracy, and success rate.
- Add real inventory APIs/RAG, API authentication, retry/backoff for transient
  errors, and a supervisor/evaluator for high-impact actions.

## Phase-completion status against `INSTRUCTOR_GUIDE.md`

| Phase | Status | Evidence / remaining work |
|---|---|---|
| Hook: chatbot limitation | **Complete** | Tool-free baseline exists; simple Gemini call is logged. Run the multi-step baseline and retain its non-grounded response for the demo. |
| Tool design | **Complete in code** | Four documented tools and `TOOL_DESIGN_EVOLUTION.md`. Quantity validation remains an improvement. |
| Agent v1 | **Implemented, not evidenced** | `--version v1` exists but no v1 execution trace is in `logs/`. |
| Agent v2 | **Implemented; Gemini verified; Phi-3 regression pending** | Gemini completed five steps correctly. Phi-3 exposed a multi-action/placeholder failure; guard and regression test added. |
| Failure analysis | **Complete in diagnosis; recovery pending** | Provider migration and a genuine Phi-3 ReAct failure are documented. A post-fix local recovery trace still needs to be captured. |
| Group evaluation | **Implemented, not run** | `evaluate.py` exists; no `evaluation_*.jsonl` result is present. |
| Provider switching | **Partially complete** | OpenAI/Gemini/local providers exist; only Gemini has a verified execution trace. |

## Commands still required before submission

```powershell
python -m pytest tests\test_agent.py -q
python tests\test_local.py
python chatbot.py --message "What is the capital of Vietnam?"
python run_agent.py --version v2 --message "I want to buy 2 iPhones using code WINNER and ship to Hanoi. What is the total price?"
python run_agent.py --version v1 --message "Buy 1 iPhone with coupon NOTREAL and ship to Hanoi. What is the total?"
python run_agent.py --version v2 --message "Buy 1 iPhone with coupon NOTREAL and ship to Hanoi. What is the total?"
python evaluate.py
```

After these commands, copy the generated failed and successful trace excerpts
from `logs/` into this report and `GROUP_REPORT_DRAFT.md`; replace all
bracketed evaluation metrics with measured values.
