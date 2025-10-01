# AGENTS.md — Agent Lab

## Project Overview

**Agent Lab** is a developer-facing Gradio v5 web application for rapidly configuring, comparing, and iterating on AI agents. It connects to OpenRouter's API to provide access to multiple LLM models with streaming chat, dynamic model catalog, session persistence, and comprehensive telemetry (latency, tokens, cost).

**Architecture**: Gradio UI → pydantic-ai Agent Runtime → OpenRouter API (OpenAI-compatible). Tools include math operations, clock, and optional web fetch with strict allow-listing.

**Tech Stack**: Python 3.11-3.12, Gradio v5, pydantic-ai, OpenAI SDK (OpenRouter), httpx

## Project Structure

```
agent-lab/
├── app.py                    # Main Gradio UI with streaming, Stop, badges
├── agents/
│   ├── runtime.py           # Agent builder, streaming runner, pricing
│   ├── tools.py             # Typed Pydantic tools (math, clock, web fetch)
│   └── models.py            # Pydantic data models (AgentConfig, RunRecord)
├── services/
│   ├── catalog.py           # Dynamic model catalog with fallback
│   └── persist.py           # Session save/load (JSON), CSV writer
├── data/
│   ├── runs.csv             # Telemetry log (auto-created)
│   └── sessions/            # Saved session JSONs
├── .env                      # OPENROUTER_API_KEY (not in repo)
└── README.md
```

## Setup and Run Commands

### Initial Setup
```bash
# Install dependencies
pip install gradio pydantic-ai openai httpx python-dotenv

# Create .env file with your OpenRouter API key
echo "OPENROUTER_API_KEY=your_key_here" > .env

# Create data directory
mkdir -p data/sessions
```

### Run Development Server
```bash
python app.py
```

**Expected behavior**: App launches on `http://localhost:7860`, dynamic model catalog fetches at start, first streamed response completes in <90s with valid API key.

### Testing
```bash
# Unit tests (when implemented)
pytest tests/ -v

# Test specific module
pytest tests/test_tools.py -v

# Test with coverage
pytest --cov=agents --cov=services tests/
```

## Code Style and Conventions

### Python Standards
- **Type hints**: All functions must use type annotations
- **Pydantic models**: Use for all data validation and serialization
- **Async where appropriate**: Streaming and HTTP operations
- **Error handling**: Graceful degradation with user-friendly messages

### Do's ✓
- Use Pydantic `BaseModel` for all structured data (configs, records)
- Validate tool inputs with typed Pydantic schemas
- Include docstrings for public functions
- Use `pathlib.Path` for file operations
- Keep streaming functions cooperative (support cancellation tokens)
- Truncate external content (4K chars for web fetch)
- Log errors with context but never expose API keys

### Don'ts ✗
- Never log or persist `OPENROUTER_API_KEY` in any form
- Don't make blocking calls in Gradio event handlers
- Don't skip input validation on tool calls
- Avoid hard-coded model lists (use dynamic catalog + fallback)
- Don't write to CSV without all required fields
- Never bypass web tool allow-list (security-critical)

### File-Specific Patterns

**`agents/tools.py`** - Example of good tool definition:
```python
from pydantic import BaseModel
from pydantic_ai import RunContext

class AddInput(BaseModel):
    a: float
    b: float

async def add_numbers(ctx: RunContext, input: AddInput) -> float:
    """Add two numbers with validation."""
    return input.a + input.b
```

**`services/persist.py`** - Session persistence pattern:
- Use `uuid4()` for session IDs
- Include timestamps in ISO format
- Preserve exact config + transcript structure

## Critical Data Contracts

### CSV Schema (data/runs.csv)
**Header (required, stable):**
```
ts,agent_name,model,prompt_tokens,completion_tokens,total_tokens,latency_ms,cost_usd,experiment_id,task_label,run_notes,streaming,model_list_source,tool_web_enabled,web_status,aborted
```

**Rules:**
- `ts` must be ISO 8601 datetime
- All token fields default to `0` if usage unavailable
- `cost_usd` computed as: `(prompt_tokens/1000)*input_price + (completion_tokens/1000)*output_price`
- `web_status` values: `off|ok|blocked`
- `aborted` flag: `true` if Stop pressed, `false` otherwise

### Web Tool Refusal Format
**Standardized text (exact match required for tests):**
```
Refused: domain '<hostname>' not in allow-list.
```

### Agent Config Structure
```python
class AgentConfig(BaseModel):
    name: str
    model: str  # OpenRouter model ID
    system_prompt: str
    temperature: float  # 0.0-2.0
    top_p: float        # 0.0-1.0
    tools: list[str] = []
    extras: dict[str, Any] = {}
```

## Streaming and Cancellation

### Key Requirements
- Use OpenAI SDK with `stream=True` for OpenRouter calls
- Emit token deltas via callback: `on_delta(str)`
- Support cooperative cancellation with shared token/flag
- Target <500ms halt time when Stop pressed
- Aggregate usage on completion or abort

### Implementation Pattern
```python
async def run_agent_stream(agent, user_text, cfg, on_delta, cancel_token):
    # Check cancel_token periodically during streaming
    # Yield deltas via on_delta(chunk)
    # On finish: return {text, usage, latency_ms}
    # On abort: return partial result with aborted=True
```

## Model Catalog

### Dynamic Fetch
- Call `GET https://openrouter.ai/api/v1/models` at app start
- Cache in memory with timestamp
- On failure: use static fallback list
- Show source in UI: "Dynamic (fetched <time>)" or "Fallback"

### Fallback Models (curated)
Include at minimum:
- `openai/gpt-4-turbo`
- `anthropic/claude-3-opus`
- `meta-llama/llama-3-70b-instruct`

### Refresh Action
- "Refresh Models" button re-fetches catalog
- Updates dropdown immediately
- Displays fetch timestamp

## Security and Privacy

### API Key Handling
- **Only** via `OPENROUTER_API_KEY` environment variable
- Never log, display in UI, or write to files/CSV
- App shows banner and disables Send if missing

### Web Fetch Tool
- **OFF by default** (toggle required)
- Strict allow-list: `{"example.com", "api.github.com", "raw.githubusercontent.com"}`
- 10s timeout with `follow_redirects=True`
- Truncate response to 4,000 chars
- Badge states: OFF (gray) → ON (blue) → OK (green) / BLOCKED (red)

### Local Data
- All sessions and CSV data stored locally in `data/`
- No external transmission of conversation history
- User manages deletion

## Git Workflow

### Branch Naming
```
feature/<short-description>
fix/<issue-description>
docs/<topic>
```

### Commit Messages
```
<type>(<scope>): <description>

Types: feat, fix, docs, refactor, test, chore
Example: feat(streaming): add cooperative cancellation
```

### Pre-commit Checklist
- [ ] All type hints present
- [ ] Pydantic models validate correctly
- [ ] No API keys in code/logs
- [ ] Tests pass (when implemented)
- [ ] Streaming works with Stop button
- [ ] CSV schema unchanged (or migration provided)

### Pull Request Requirements
1. **Description**: What changed and why
2. **Testing**: Evidence of manual testing or new unit tests
3. **Breaking changes**: Clearly marked if CSV schema or config changes
4. **Security**: Confirm no secrets exposed

## Common Gotchas and Troubleshooting

### Streaming Issues
- **Problem**: Gradio not updating during stream
- **Fix**: Use `yield` with proper event handlers, check cancel token

### Model Usage Missing
- **Problem**: Some models don't return token counts
- **Fix**: Default to `0` for tokens, still log latency and model ID

### Web Tool Blocked
- **Problem**: Badge turns red, domain refused
- **Fix**: Add domain to allow-list constant or ask user to confirm

### Session Load Failures
- **Problem**: JSON parse error on load
- **Fix**: Validate session schema version, handle legacy formats gracefully

### Pricing Drift
- **Problem**: Cost calculations incorrect
- **Fix**: Update pricing registry in `agents/runtime.py`, future: auto-sync from OpenRouter

## When Stuck

1. **Check the PRD/TRD**: Detailed specs in `PRD.md` and `TRD.md`
2. **Review existing patterns**: Look at implemented tools/services
3. **Ask clarifying questions**: Don't guess on ambiguous requirements
4. **Propose a plan**: Outline approach before implementing large changes
5. **Security first**: When in doubt about API keys or web fetch, default to most restrictive

## Testing Strategy

### TDD Workflow Implementation
Following Test-Driven Development principles across all implementation phases:

#### Red-Green-Refactor Cycle
1. **Red**: Write failing test defining desired behavior
2. **Green**: Implement minimal code to pass test
3. **Refactor**: Improve code while maintaining coverage

#### Test Categories in TDD Context
- **Unit Tests (Priority)**: Test individual functions/classes in isolation
  - Tool input validation (Pydantic schemas)
  - Pricing math (edge cases: 0 tokens, unknown model)
  - CSV header initialization and append
  - Web tool refusal text exact match
  - Catalog: success, failure → fallback

- **Integration Tests**: Test component interactions and workflows
  - Streaming E2E with cancellation
  - Web badge state transitions
  - Session save → load → identical config
  - CSV contains all required fields

- **Acceptance Tests**: Validate end-to-end user scenarios

#### Coverage Requirements
- Maintain >90% coverage for `agents/` and `services/` directories
- Run coverage verification before each commit
- Address coverage gaps during refactoring phase

### Manual QA
- Stop button halts within ~500ms
- Dynamic catalog refresh updates dropdown
- Token/latency match stopwatch measurements
- Export CSV opens correctly in spreadsheet tools

## Phase Implementation Order

Follow the rollout plan from PRD Section 13:

1. **Phase 0**: Gradio UI shell, config state, CSV init
2. **Phase 1**: Tools (math, clock) + web fetch toggle
3. **Phase 2**: Streaming with SSE + Stop button
4. **Phase 3**: Dynamic model catalog + refresh
5. **Phase 4**: Session persistence + run tagging
6. **Phase 5**: UX polish (spinners, microcopy)

Work phase-by-phase to maintain stability and testability.
