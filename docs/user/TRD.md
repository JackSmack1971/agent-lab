# TRD — Agent Lab (Gradio 5 × pydantic-ai × OpenRouter)

## 1) System Architecture

### 1.1 Components

* **UI/Client:** Gradio v5 Blocks app with `Chatbot`, `DownloadButton`, and control widgets. Supports streaming token rendering and a Stop action. ([gradio.app][1])
* **Agent Runtime:** `pydantic-ai` `Agent` with typed `Tool`s (`add_numbers`, `utc_now`, optional `fetch_url`). Built on OpenAI-compatible client. Provides retries and tool registration APIs. ([ai.pydantic.dev][2])
* **Model Gateway:** OpenRouter API via OpenAI Python SDK, with `base_url=https://openrouter.ai/api/v1`, streaming enabled when requested. ([OpenRouter][3])
* **Services:**

  * **Model Catalog:** fetches available models list at runtime; caches with fallback list. ([OpenRouter][4])
  * **Persistence:** sessions saved/loaded as JSON; run telemetry appended to CSV.
  * **Networking:** `httpx` client for safe allow-listed HTTP GETs (follow redirects explicitly; bounded timeout). ([python-httpx.org][5])

### 1.2 Data Flow (Streaming turn)

1. User submits message ? UI allocates a cancel token and shows “generating…”.
2. Runtime calls OpenRouter (OpenAI-compatible Chat Completions) with `stream=true`; UI consumes SSE chunks and updates the `Chatbot`. ([OpenRouter][6])
3. On completion (or Stop), runtime aggregates usage (tokens if provided), computes latency & cost, updates right-panel, appends to CSV. ([OpenRouter][3])
4. If a tool is invoked, pydantic-ai validates args and calls the Python handler; Web tool enforces domain allow-list and truncates output. ([ai.pydantic.dev][7])

---

## 2) External Interfaces

### 2.1 OpenRouter (OpenAI-compatible)

* **Base URL:** `https://openrouter.ai/api/v1` (set on OpenAI client). ([OpenRouter][3])
* **Streaming:** request param `stream: true`; server emits chunked deltas. ([OpenRouter][6])
* **Usage & Pricing Notes:** Responses may include token usage; pricing depends on model, with catalog/pricing metadata available via Models API and site. Reasoning tokens—if returned—are counted as output tokens for billing. ([OpenRouter][3])

### 2.2 Model Catalog API

* **List models:** `GET /api/v1/models` ? returns normalized array with IDs, names, and supported parameters; cache at edge. Used to dynamically populate the model dropdown. ([OpenRouter][4])
* **Per-model endpoints:** optional lookup of provider endpoints for diagnostics. ([OpenRouter][8])

### 2.3 Gradio UI Contracts

* **`Chatbot`** renders streamed tokens; supports text & basic markdown.
* **`DownloadButton`** emits a local file path as output to trigger downloads. ([gradio.app][9])

### 2.4 HTTPX (Web Tool)

* **Redirects:** disabled by default; explicitly set `follow_redirects=True`.
* **Timeouts:** pass finite per-request or client timeouts. ([python-httpx.org][5])

---

## 3) Detailed Requirements

### 3.1 UI/UX (Gradio v5)

* **Layout:**

  * Left: Agent Config (Name, Model [Dynamic], System Prompt, `temperature`, `top_p`, Web-tool toggle).
  * Center: Chat with **streaming** and **Stop**.
  * Right: Run Info (latency • tokens • $/run), **Web Tool badge** (OFF/ON/blocked/ok), **Download runs.csv**. ([gradio.app][1])
* **Streaming:** token-level updates (?60ms UI cadence) and cooperative cancellation. ([gradio.app][10])
* **Badging:** OFF (gray), ON (blue/green), blocked (red) based on last action.

### 3.2 Agent Runtime (pydantic-ai)

* **Agent Construction:**

  * Inputs: `system_prompt`, `model`, `temperature`, `top_p`, `tools`.
  * Tools defined via Pydantic schemas and registered with `Agent`. ([ai.pydantic.dev][2])
* **Retries:** Use library’s tool/output-validation retry knobs; HTTP request retries may be layered at client level if desired. ([ai.pydantic.dev][11])

### 3.3 Model Catalog

* **Fetch:** On app start + “Refresh Models”.
* **Fallback:** Static curated list if network/API fails.
* **Cache:** In-memory with timestamp; indicate “Dynamic (fetched <time>) / Fallback” under dropdown. ([OpenRouter][4])

### 3.4 Persistence

* **Sessions:** JSON `{id, created_at, agent_config, transcript[{role,content,ts}], model_id, notes?}` saved to `data/sessions/`.
* **Runs:** Append CSV rows to `data/runs.csv` with stable schema (see §4.2).

### 3.5 Web Fetch Tool

* **Allow-list:** e.g., `{example.com, api.github.com, raw.githubusercontent.com}`.
* **Networking:** `httpx.Client(follow_redirects=True, timeout=...)`.
* **Output:** Truncate to ?4,000 chars; standardized refusal text if host not allowed. ([python-httpx.org][5])

---

## 4) Data Contracts

### 4.1 Pydantic Models

```python
class AgentConfig(BaseModel):
    name: str
    model: str        # OpenRouter model id
    system_prompt: str
    temperature: float
    top_p: float
    tools: list[str] = []
    extras: dict[str, Any] = {}

class RunRecord(BaseModel):
    ts: datetime
    agent_name: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    cost_usd: float
    experiment_id: str | ""
    task_label: str | ""
    run_notes: str | ""
    streaming: bool
    model_list_source: Literal["dynamic","fallback"]
    tool_web_enabled: bool
    web_status: Literal["off","ok","blocked"]
    aborted: bool = False
```

### 4.2 CSV Schema (`data/runs.csv`)

```
ts,agent_name,model,prompt_tokens,completion_tokens,total_tokens,latency_ms,cost_usd,
experiment_id,task_label,run_notes,streaming,model_list_source,tool_web_enabled,web_status,aborted
```

### 4.3 OpenRouter Models API (response shape)

* Root `data: [Model...]` plus metadata (ID, name, description, pricing/params). Used for dropdown population and pricing hints. ([OpenRouter][12])

---

## 5) Algorithms & Logic

### 5.1 Streaming Aggregation

* Maintain a buffer for token deltas; update UI per chunk.
* On final chunk: compute `latency_ms = (t_end - t_start)`; extract usage tokens if present; write CSV. ([OpenRouter][6])

### 5.2 Cost Estimation

```
cost_usd = (prompt_tokens/1000)*input_price + (completion_tokens/1000)*output_price
```

* Price table keyed by model ID. If unknown, omit `$` or set `0.0`. (Model pricing available in catalog/site; reasoning tokens count as output tokens.) ([OpenRouter][12])

### 5.3 Web Badge State

* OFF ? `web_status="off"`.
* ON + allowed fetch ? `"ok"`.
* ON + blocked (refusal string found) ? `"blocked"`.

---

## 6) Error Handling & Edge Cases

| Case                         | Handling                                                                                            |
| ---------------------------- | --------------------------------------------------------------------------------------------------- |
| Missing `OPENROUTER_API_KEY` | UI banner; disable Send until set.                                                                  |
| Catalog fetch fails          | Log warning; use fallback model list; mark `model_list_source="fallback"`. ([OpenRouter][4])        |
| Streaming interrupted (Stop) | Set `aborted=True`; do not write row **or** write flagged row per config; clear spinner.            |
| Tool input validation error  | Show concise error; allow user to retry; rely on pydantic-ai schema errors. ([ai.pydantic.dev][7])  |
| HTTP 30x/40x/50x in Web tool | Follow redirects if enabled; return status text when ?400; cap body length. ([python-httpx.org][5]) |
| Usage fields absent          | Default tokens to 0; still write latency; mark `$` unknown. ([OpenRouter][3])                       |

---

## 7) Security & Privacy

* **Secrets:** Only via environment; never logged or persisted.
* **Web tool:** strict allow-list; finite timeouts; content truncation; clear refusal message. ([python-httpx.org][5])
* **Local-only data:** sessions/CSV stay on disk; user manages deletion.
* **Streaming:** no PII redaction provided—document risk in README.

---

## 8) Performance Targets

* **Start-to-first-token:** ?1.5s p50 for typical models (network + provider SLA). ([OpenRouter][6])
* **UI update cadence:** ?60ms per chunk (single Chatbot render per delta batch). ([gradio.app][10])
* **Overhead:** non-blocking UI callbacks; CSV append ?10ms.

---

## 9) Implementation Plan (Tech Tasks)

1. **Client Setup**

   * OpenAI SDK client with OpenRouter `base_url`. Streaming toggle per request. ([OpenRouter][3])
2. **Agent Runtime**

   * Build `Agent` with tools registered; expose `run_agent_stream(on_delta, cancel_token)`. ([ai.pydantic.dev][2])
3. **Gradio UI**

   * Blocks layout; `Chatbot` streaming; Stop button; badge HTML; `DownloadButton` for CSV. ([gradio.app][10])
4. **Model Catalog Service**

   * `GET /api/v1/models` with in-memory cache + fallback. ([OpenRouter][4])
5. **Pricing Registry**

   * Local dict keyed by model ID; optional enrichment from catalog/site. ([OpenRouter][12])
6. **Persistence**

   * `save_session/load_session` (JSON), CSV writer with header init.
7. **Web Tool**

   * `httpx.Client(follow_redirects=True, timeout=10)`; allow-list enforcement & truncation. ([python-httpx.org][5])
8. **QA Hooks**

   * Dev console toggle for tool calls; latency stopwatch debug.

---

## 10) Test Plan (Selected)

* **Unit**

  * Catalog success/failure ? `dynamic|fallback` source. ([OpenRouter][4])
  * Tool schema validation and refusal string consistency. ([ai.pydantic.dev][7])
  * HTTPX redirect & timeout behavior. ([python-httpx.org][5])
* **Integration**

  * Streaming E2E: deltas accumulate to final text; Stop cancels within ~500ms. ([OpenRouter][6])
  * Web badge transitions on allowed vs blocked host.
  * CSV rows include all mandatory fields; pricing included when known.
* **Manual**

  * Model dropdown “Dynamic (fetched <time>) / Fallback” label changes after `Refresh`. ([OpenRouter][4])

---

## 11) Deliverables

* `app.py` (Gradio UI with streaming, Stop, badge, export)
* `agents/runtime.py` (Agent builder, streaming runner, pricing)
* `agents/tools.py` (typed tools; web fetch w/ allow-list)
* `agents/models.py` (Pydantic models)
* `services/catalog.py`, `services/persist.py`
* `data/runs.csv` (created on first run), `data/sessions/`
* `README.md` (setup, streaming, catalog, security caveats), `docs/developer/AGENTS.md`

---

## 12) Open Items

* Decide CSV policy on Stop (skip row vs. write `aborted=true`).
* Optional: surface provider endpoint diagnostics using per-model endpoint API for debugging. ([OpenRouter][8])

---

### References

OpenRouter quickstart/overview; streaming; models API; reasoning tokens; models site. ([OpenRouter][13])
pydantic-ai agents/tools APIs. ([ai.pydantic.dev][2])
Gradio docs: Blocks, Chatbot, DownloadButton, streaming guide. ([gradio.app][1])
HTTPX redirects/timeouts API. ([python-httpx.org][5])

[1]: https://www.gradio.app/docs?utm_source=chatgpt.com "Gradio Documentation"
[2]: https://ai.pydantic.dev/agents/?utm_source=chatgpt.com "Agents"
[3]: https://openrouter.ai/docs/api-reference/overview?utm_source=chatgpt.com "OpenRouter API Reference | Complete API Documentation"
[4]: https://openrouter.ai/docs/api-reference/list-available-models?utm_source=chatgpt.com "List available models | OpenRouter | Documentation"
[5]: https://www.python-httpx.org/compatibility/?utm_source=chatgpt.com "Requests Compatibility Guide"
[6]: https://openrouter.ai/docs/api-reference/streaming?utm_source=chatgpt.com "API Streaming | Real-time Model Responses in OpenRouter"
[7]: https://ai.pydantic.dev/tools/?utm_source=chatgpt.com "Function Tools"
[8]: https://openrouter.ai/docs/api-reference/list-endpoints-for-a-model?utm_source=chatgpt.com "List endpoints for a model"
[9]: https://www.gradio.app/docs/gradio/chatbot?utm_source=chatgpt.com "Chatbot - Gradio Docs"
[10]: https://www.gradio.app/guides/creating-a-custom-chatbot-with-blocks?utm_source=chatgpt.com "Creating A Custom Chatbot With Blocks"
[11]: https://ai.pydantic.dev/api/agent/?utm_source=chatgpt.com "pydantic_ai.agent"
[12]: https://openrouter.ai/docs/models?utm_source=chatgpt.com "Access 400+ AI Models Through One API"
[13]: https://openrouter.ai/docs/quickstart?utm_source=chatgpt.com "OpenRouter Quickstart Guide | Developer Documentation"
