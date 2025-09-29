# PRD — Agent Lab (Gradio 5 × pydantic-ai × OpenRouter)

## 1) Overview
**Goal.** Build a developer-facing **Agent Lab** to rapidly configure, compare, and iterate on AI agents (system prompts, models, tools) with **streaming chat**, **dynamic model catalog**, **session persistence**, and **per-run telemetry** (latency, tokens, cost) + **tagging** for A/B analysis.

**Primary outcome.** A Gradio v5 web app where users can:
- Create/edit agent configs (name, model, system prompt, decoding params, tool toggles)
- Chat with the agent with **SSE streaming** (+ Stop)
- Capture **usage metrics** and compute **effective $/run**
- **Export** comparison data (CSV) and **persist/load** sessions (JSON)
- Toggle **Web Fetch tool** per session (**OFF by default**) with a status badge

**Audience.** AI engineers, prompt engineers, research/product teams.

**Non-goals (V1).**
- Multi-tenant auth, RBAC, team sharing
- Fine-tuning management
- Complex external tools/RAG beyond demo HTTP GET

---

## 2) Success Metrics (V1)
- **Setup-to-first-response** ? 90s (local dev) with valid API key
- **Median turn latency** surfaced per run; **p50** ? model SLA + 500 ms UI overhead
- **Zero-error sessions** ? 98% (graceful tool & network errors)
- **Export coverage** ? 95% of successful runs present in `runs.csv` with latency & token fields
- **Prompt reproducibility:** At `temperature=0`, outputs stable within model determinism limits
- **Streaming UX:** Start-to-first-token ? 1.5s on p50 for standard models

---

## 3) Users & Use Cases
### 3.1 Personas
- **Prompt Engineer (primary):** Iterates on system prompts; compares models per task
- **Research Engineer:** Needs token/cost/latency measurements; sanity-checks tool behavior
- **Product Manager:** Reviews A/B grids, costs, and tradeoffs

### 3.2 Top Use Cases
1) **Model Bake-off:** Same prompt across models; export CSV for analysis
2) **Prompt Tuning:** Adjust system prompt/decoding; evaluate quality vs. cost/latency
3) **Tool Behavior Check:** Verify Math/Clock and optional Web Fetch (allow-listed)
4) **Cost Profiling:** Track $/run vs. latency/tokens for workflow economics
5) **Session Persistence:** Save/load sessions to reproduce runs & share artifacts

---

## 4) Scope & Requirements
### 4.1 Functional Requirements
- **F1. Agent Config**
  - Name, model selector (**dynamic catalog** + fallback + refresh)
  - System prompt (multiline)
  - Decoding params: `temperature`, `top_p`
  - Tools: `add_numbers`, `utc_now`, `fetch_url` (toggle; **OFF by default**)
  - Build/Reset agent to apply changes

- **F2. Chat (Streaming)**
  - SSE **streaming** of assistant tokens into Chat
  - **Stop** button cancels in-flight generation (~?500 ms to halt)
  - Non-stream fallback if streaming unavailable

- **F3. Telemetry**
  - Per run: timestamps, prompt/completion/total tokens, latency (ms), model id, agent name, **estimated cost**
  - Append row to `data/runs.csv`
  - Right panel shows latest run info

- **F4. Pricing/Cost**
  - Model?(input/output per-1K tokens) price table
  - `cost_usd = in_tokens/1000*in_price + out_tokens/1000*out_price`
  - Show in panel and export to CSV

- **F5. Web Tool Status Chip**
  - Badge shows **OFF/ON**
  - If ON and a request is **refused** (non-allow-listed domain), badge turns **red**
  - If ON and successful, badge turns **green**
  - Standardized refusal text: `Refused: domain '<host>' not in allow-list.`

- **F6. Export**
  - Download `runs.csv` button
  - Stable column schema (see §8.2)

- **F7. Session Persistence**
  - **Save Session:** writes `{config, transcript, timestamps, model_id}` to `data/sessions/{uuid}.json`
  - **Load Session:** restores config + transcript
  - **New Session:** clears transcript; preserves current config

- **F8. Run Tagging**
  - Inputs: `experiment_id` (text), `task_label` (free-text or select), `run_notes` (textarea)
  - Tags written to CSV per run and displayed near Run Info

- **F9. Dynamic Model Catalog**
  - Fetch available models at app start and on **Refresh Models**
  - Cache in memory with timestamp; fallback to curated static list on failure
  - Dropdown displays friendly `display_name` (or `id`) with provider tag

### 4.2 Non-Functional Requirements
- **N1. Reliability:** Graceful handling for network/API errors, missing key, invalid inputs; fallback catalog
- **N2. Security:** No API keys in logs/UI/files; Web Fetch allow-list; truncate remote content to 4K chars; timeouts
- **N3. Performance:** UI interactions < 100 ms (excl. model latency); streaming updates target ? 60 ms cadence
- **N4. Portability:** Python 3.11–3.12; local launch via `python app.py`
- **N5. Code Quality:** Typed Pydantic models; modular files; isolated streaming & catalog services

---

## 5) Architecture
### 5.1 Components
- **UI Layer (Gradio v5/Blocks)**
  - Sidebar: Config, tool toggle, **Run Tagging**, Model **Refresh**, Session actions (Save/Load/New)
  - Center: **Streaming Chat** (Chatbot), input, Send, **Stop**
  - Right: Run Info, **Web Tool badge**, Export
  - Hidden state: `AgentConfig`, `Agent`, `history`, catalog cache, cancel token

- **Runtime Layer (pydantic-ai)**
  - `Agent` binds model+prompt+tools
  - Tools registered via typed Pydantic schemas

- **Model Client**
  - OpenAI SDK with `base_url=https://openrouter.ai/api/v1`
  - Model id from dropdown

- **Services**
  - **Streaming Runner:** `run_agent_stream()` yields token deltas + final usage; supports cancellation
  - **Model Catalog:** `list_models()` with cache + fallback
  - **Persistence:** `save_session()`, `load_session()`

- **Telemetry**
  - `RunRecord` Pydantic model; pricing service; CSV writer

### 5.2 Data Flow (Streaming)
1) User presses **Send** ? create run context with tags
2) `run_agent_stream()` starts ? emits deltas to UI; **Stop** triggers cancellation token
3) On finish/stop, runtime aggregates usage/latency ? computes cost ? updates panel & CSV (see aborted handling in §12 Testing)

---

## 6) UX & Interaction
- **Left (Config):** Name, dynamic Model dropdown (caption: “Source: Dynamic (fetched <time>) / Fallback”), System Prompt (6–10 lines), Temperature, Top-p, **Web tool toggle (OFF)**, **Run tags**, Build/Reset, **Refresh Models**, **Save/Load/New Session**
- **Center (Chat):** Streaming transcript, input, **Send**, **Stop**
- **Right (Telemetry):** **Web Tool badge** (OFF/ON/blocked/ok), latest `latency • tokens • $/run`, **Download runs.csv**
- **Feedback:** Inline errors for missing key, blocked domain, HTTP failures; status messages on Build/Reset, Stop

---

## 7) Configuration & Environment
- **Secrets:** `OPENROUTER_API_KEY` via `.env`
- **Pricing Table:** Local dict (maintained manually in V1)
- **Allow-list:** `{"example.com","api.github.com","raw.githubusercontent.com"}` (editable constant)
- **Directories:** `data/` (auto-created), `data/sessions/`

---

## 8) Data Model & Storage
### 8.1 Pydantic Models
- **AgentConfig**
  - `name: str`
  - `model: str`
  - `system_prompt: str`
  - `temperature: float`
  - `top_p: float`
  - `tools: List[str]` (informational)
  - `extras: Dict[str, Any]`

- **RunRecord**
  - `ts: datetime`
  - `agent_name: str`
  - `model: str`
  - `prompt_tokens: int`
  - `completion_tokens: int`
  - `total_tokens: int`
  - `latency_ms: int`
  - `cost_usd: float`
  - **Tags:** `experiment_id: str`, `task_label: str`, `run_notes: str | ''`
  - **Meta:** `streaming: bool`, `model_list_source: Literal['dynamic','fallback']`
  - **Optional:** `aborted: bool` (if Stop pressed before completion)

- **Session (JSON)**
  - `id, created_at, agent_config, transcript[{role,content,ts}], model_id, notes?`

### 8.2 CSV Schema (`data/runs.csv`)
Header (V1):
ts,agent_name,model,prompt_tokens,completion_tokens,total_tokens,latency_ms,cost_usd,experiment_id,task_label,run_notes,streaming,model_list_source,tool_web_enabled,web_status

Field notes:
- `web_status`: `off|ok|blocked`
- `tool_web_enabled`: `true|false`
- *(Optional extra column if enabled)* `aborted: true|false`

---

## 9) API Contracts (internal)
- **`build_agent(cfg: AgentConfig, include_web: bool) -> Agent`**
- **`run_agent_stream(agent, user_text: str, cfg: AgentConfig, on_delta: Callable, cancel_token) -> FinalResult`**
  - Emits token deltas via `on_delta(str)`; returns `{text, usage?, latency_ms}`
- **`estimate_cost(model: str, in_toks: int, out_toks: int) -> float`**
- **`list_models(force_refresh: bool=False) -> tuple[list[ModelInfo], source: 'dynamic'|'fallback']`**
- **`save_session(session_obj) -> Path`**, **`load_session(path: Path) -> Session`**

**Tools**
- `add_numbers(AddInput{a,b}) -> float`
- `utc_now(NowInput{fmt?}) -> str`
- `fetch_url(FetchInput{url,timeout_s}) -> str` (allow-list; 4K truncation; standardized refusal text)

---

## 10) Pricing & Costing
- **Registry:** `model -> (input_per_1k, output_per_1k)`
- **Computation:** `cost_usd = (in/1000)*in_price + (out/1000)*out_price`
- **Display:** Right panel includes cost when pricing known; hides `$` otherwise
- **Maintenance:** Manual in V1; plan auto-sync later

---

## 11) Security, Privacy, Compliance
- **API key:** Environment-only; never displayed or persisted
- **Web tool:** Strict allow-list; 10s default timeout; follow redirects; 4K truncation; standardized refusal
- **PII:** Advise users not to paste secrets; local-only storage
- **Auditability:** Runs logged locally; user-controlled deletion of `data/`

---

## 12) Observability, Errors, Testing
### Error Handling
- Missing API key ? UI banner + disabled Send
- Catalog fetch failure ? warning + fallback list
- Tool blocked domain ? red badge + refusal text
- HTTP failures ? inline message with status code

### Testing Strategy
- **Unit**
  - Tools validate inputs; refusal format exact match
  - Pricing math (rounding; unknown model ? 0)
  - CSV header init; append correctness
  - Catalog: success, failure ? cache & fallback
- **Integration**
  - **Streaming** E2E: incremental updates; final aggregation of usage/cost
  - **Stop** mid-stream: ensure cancel; decide CSV policy:
    - If `aborted=true` enabled ? write row with partial tokens and flag
    - Otherwise ? no row on abort
  - **Persistence**: save ? load ? identical `AgentConfig` & transcript
  - **Web badge** transitions: OFF?gray, ON?blue/green, blocked?red
- **Manual QA**
  - Token/latency sanity vs stopwatch
  - Dynamic catalog refresh without restart

---

## 13) Rollout Plan
- **Phase 0 (Scaffold):** UI shell, config state, CSV init
- **Phase 1 (Tools):** Math/Clock; Web Fetch (toggle OFF) + status badge
- **Phase 2 (Streaming):** SSE runner + Stop + non-stream fallback
- **Phase 3 (Catalog):** Dynamic fetch + refresh + fallback
- **Phase 4 (Persistence & Tagging):** Save/Load sessions; run tags integrated into CSV
- **Phase 5 (Polish):** UX microcopy, spinners, small accessibility fixes

---

## 14) Risks & Mitigations
- **R1: Missing usage fields** on some models ? default zeros; mark N/A; allow manual notes
- **R2: Pricing drift** ? central registry; config override; future auto-sync
- **R3: Web tool misuse** ? allow-list; visible badge; off by default; truncate outputs
- **R4: Non-determinism** ? recommend `temperature=0` for A/B
- **R5: Streaming cancel lag** ? cooperative cancellation token + short polling window

---

## 15) Documentation & DevEx
- **README:** setup, `.env`, launch, dynamic catalog notes, streaming & Stop, persistence paths
- **AGENTS.md:** prompt conventions; tool usage guidance; reproducibility tips
- **CONTRIBUTING.md:** adding tools/pricing entries; coding standards; tests
- **Examples/** canned configs & prompts for bake-offs; sample sessions JSON

---

## 16) Acceptance Criteria (V1)
- [ ] App launches; first streamed response completes with configured model
- [ ] **Web tool OFF by default**; toggling ON + Build/Reset enables fetch
- [ ] **Badge states**: OFF (gray), ON (blue/green), blocked (red)
- [ ] **Dynamic catalog** loads at start; **Refresh Models** updates dropdown; fallback used on provider error
- [ ] **Persistence**: Save/Load restores config + transcript identically
- [ ] **Tagging**: `experiment_id`, `task_label`, `run_notes` included in each CSV row
- [ ] **CSV** rows have `ts, model, total_tokens, latency_ms`; cost present when pricing known
- [ ] **Stop** halts generation within ~500 ms (and either logs `aborted=true` or writes no row per policy)
- [ ] No plaintext API key in logs/UI/files

---

## 17) Open Questions
1) Should we **track `aborted`** runs in CSV (`true|false`) or skip CSV writes on Stop?
2) Should `task_label` be **free text** only or a **chips selector** (persist common labels)?
3) Do we display a **dev console panel** for tool-call traces (toggleable) in V1 or defer?
