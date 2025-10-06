# Function Specifications for Agent-Lab Test Fixes

## 1. Streaming Cancellation Fixes

### Function: `run_agent_stream_fixed`
**Location**: `agents/runtime.py`

**Signature**:
```python
async def run_agent_stream_fixed(
    agent: Agent,
    user_message: str,
    on_delta: Callable[[str], None],
    cancel_token: Event,
    correlation_id: str | None = None,
) -> StreamResult
```

**Parameters**:
- `agent`: Configured pydantic-ai Agent instance
- `user_message`: User input string to stream through agent
- `on_delta`: Callback function called with each text delta
- `cancel_token`: Threading.Event for cancellation signaling
- `correlation_id`: Optional UUID for request tracing

**Returns**:
- `StreamResult`: Dataclass containing text, usage, latency, and abort status

**Behavior**:
- Checks cancellation token BEFORE processing each chunk/delta
- Accumulates text only when not cancelled
- Provides immediate abortion without partial text accumulation
- Handles both `agent.run(stream=True)` and `agent.run_stream()` patterns
- Includes comprehensive error handling and logging

**Error Handling**:
- Raises `RuntimeError` for agent initialization failures
- Logs errors but continues processing for non-critical issues
- Ensures proper cleanup of async contexts

---

### Function: `RealisticDelayedStream`
**Location**: `tests/integration/test_streaming_cancellation.py`

**Signature**:
```python
class RealisticDelayedStream:
    def __init__(self, chunks: list[str], delay_between_chunks: float = 0.01)
    async def __anext__(self) -> Mock
```

**Parameters**:
- `chunks`: List of text chunks to yield
- `delay_between_chunks`: Delay between yielding chunks

**Behavior**:
- Yields mock chunks with realistic async delays
- Allows cancellation testing with proper timing
- Simulates network/streaming latency

---

## 2. UI Integration Fixes

### Function: `send_message_streaming_fixed`
**Location**: `app.py`

**Signature**:
```python
async def send_message_streaming_fixed(
    message: str,
    history: list[list[str]] | None,
    config_state: AgentConfig,
    model_source_enum: str,
    agent_state: Any,
    cancel_event_state: Event | None,
    is_generating_state: bool,
    experiment_id: str,
    task_label: str,
    run_notes: str,
    id_mapping: dict
) -> AsyncGenerator[tuple, None]
```

**Parameters**:
- `message`: User input message
- `history`: Chat history as list of [user, assistant] pairs
- `config_state`: AgentConfig with model settings
- `model_source_enum`: Source of model list ("dynamic"|"fallback")
- `agent_state`: Cached agent instance
- `cancel_event_state`: Cancellation event
- `is_generating_state`: Current generation flag
- `experiment_id`: Experiment identifier
- `task_label`: Task categorization label
- `run_notes`: Additional run notes
- `id_mapping`: Model ID to display name mapping

**Yields**:
- Tuple of UI state updates for Gradio components

**Behavior**:
- Validates input before processing
- Checks cancellation token before streaming starts
- Manages UI state transitions properly
- Handles errors gracefully with user-friendly messages
- Persists run data asynchronously
- Provides detailed status updates throughout process

---

### Function: `ThreadSafeLoadingStateManager`
**Location**: `app.py`

**Signature**:
```python
class ThreadSafeLoadingStateManager:
    async def start_loading(self, operation_id: str, component: str) -> dict
    async def complete_loading(self, operation_id: str) -> dict
    async def cancel_loading(self, operation_id: str) -> dict
```

**Methods**:
- `start_loading`: Begin loading state for operation
- `complete_loading`: End loading state successfully
- `cancel_loading`: End loading state due to cancellation

**Behavior**:
- Uses asyncio.Lock for thread-safe state management
- Prevents race conditions in concurrent UI operations
- Tracks operation state with timestamps
- Returns appropriate UI state dictionaries

---

## 3. Security Validation Fixes

### Function: `validate_agent_name_comprehensive`
**Location**: `app.py`

**Signature**:
```python
def validate_agent_name_comprehensive(name: str) -> dict
```

**Parameters**:
- `name`: Agent name string to validate

**Returns**:
- Dict with "is_valid" boolean and "message" string

**Validation Rules**:
- Unicode normalization (NFKC)
- Length limits (1-100 characters)
- No control characters
- XSS pattern detection (expanded set)
- SQL injection pattern detection
- Path traversal prevention
- Allowed character set validation

---

### Function: `validate_system_prompt_comprehensive`
**Location**: `app.py`

**Signature**:
```python
def validate_system_prompt_comprehensive(prompt: str) -> dict
```

**Parameters**:
- `prompt`: System prompt string to validate

**Returns**:
- Dict with validation result

**Validation Rules**:
- Length limit (10,000 characters)
- Prompt injection pattern detection
- Code execution pattern detection
- Override instruction detection

---

### Function: `validate_temperature_robust`
**Location**: `app.py`

**Signature**:
```python
def validate_temperature_robust(value: Any) -> dict
```

**Parameters**:
- `value`: Temperature value (string, int, float, or None)

**Returns**:
- Dict with validation result

**Validation Rules**:
- Type coercion with error handling
- Range validation (0.0 to 2.0)
- Precision limits
- String parsing for numeric input

---

## 4. Session Handling Fixes

### Function: `_coerce_int_robust`
**Location**: `services/persist.py`

**Signature**:
```python
def _coerce_int_robust(value: str) -> int
```

**Parameters**:
- `value`: String value to convert to integer

**Returns**:
- Integer value or 0 on failure

**Behavior**:
- Handles empty/whitespace strings
- Converts float strings to integers
- Graceful error handling with logging

---

### Function: `_coerce_float_robust`
**Location**: `services/persist.py`

**Signature**:
```python
def _coerce_float_robust(value: str) -> float
```

**Parameters**:
- `value`: String value to convert to float

**Returns**:
- Float value or 0.0 on failure

**Behavior**:
- Handles empty strings gracefully
- Robust float parsing with error logging

---

### Function: `_coerce_bool_robust`
**Location**: `services/persist.py`

**Signature**:
```python
def _coerce_bool_robust(value: str) -> bool
```

**Parameters**:
- `value`: String value to convert to boolean

**Returns**:
- Boolean value

**Behavior**:
- Comprehensive truthy/falsy value recognition
- Case-insensitive parsing
- Defaults to False for unrecognized values

---

### Function: `_parse_row_robust`
**Location**: `services/persist.py`

**Signature**:
```python
def _parse_row_robust(row: dict[str, str]) -> RunRecord | None
```

**Parameters**:
- `row`: Dictionary of CSV row data

**Returns**:
- RunRecord instance or None on failure

**Behavior**:
- Validates required fields
- Robust type coercion for all fields
- Comprehensive error handling
- Returns None for invalid rows

---

### Function: `save_session_atomic`
**Location**: `services/persist.py`

**Signature**:
```python
async def save_session_atomic(
    session_name: str,
    config: AgentConfig,
    history: list[list[str]],
    session_dir: Path
) -> Session
```

**Parameters**:
- `session_name`: Name for the session
- `config`: Agent configuration
- `history`: Chat history
- `session_dir`: Directory to save session

**Returns**:
- Created Session instance

**Behavior**:
- Validates input parameters
- Creates session with proper transcript format
- Atomic write using temporary files
- Comprehensive error handling with cleanup

---

### Function: `load_session_atomic`
**Location**: `services/persist.py`

**Signature**:
```python
async def load_session_atomic(session_id: str, session_dir: Path) -> Session
```

**Parameters**:
- `session_id`: Session identifier
- `session_dir`: Directory containing sessions

**Returns**:
- Loaded Session instance

**Behavior**:
- Validates session file existence
- Parses and validates JSON content
- Ensures session integrity
- Comprehensive error handling

---

## 5. Content Truncation Fixes

### Function: `fetch_url_encoding_aware`
**Location**: `agents/tools.py`

**Signature**:
```python
async def fetch_url_encoding_aware(ctx: RunContext, input: FetchInput) -> str
```

**Parameters**:
- `ctx`: Pydantic-ai run context
- `input`: FetchInput with URL and timeout

**Returns**:
- Fetched content string or error message

**Behavior**:
- Domain allow-list validation
- Encoding-aware content retrieval
- Safe truncation at character boundaries
- Proper error handling for encoding issues

---

### Function: `is_allowed_content_type`
**Location**: `agents/tools.py`

**Signature**:
```python
def is_allowed_content_type(content_type: str) -> bool
```

**Parameters**:
- `content_type`: HTTP content-type header value

**Returns**:
- Boolean indicating if content type is allowed

**Behavior**:
- Validates content types suitable for text processing
- Allows text/* and specific application types
- Rejects binary content types

---

### Function: `fetch_url_with_content_validation`
**Location**: `agents/tools.py`

**Signature**:
```python
async def fetch_url_with_content_validation(ctx: RunContext, input: FetchInput) -> str
```

**Parameters**:
- `ctx`: Pydantic-ai run context
- `input`: FetchInput with URL and timeout

**Returns**:
- Fetched and validated content string

**Behavior**:
- Domain validation
- Content-type validation
- Encoding detection and validation
- Size limits and truncation
- Comprehensive error handling

---

## Integration Points

### Dependencies
- `httpx` for HTTP client functionality
- `pydantic` for input validation
- `pydantic_ai` for agent integration
- `loguru` for structured logging
- `asyncio` for async operations
- `aiofiles` for async file operations

### Error Handling Strategy
- Graceful degradation for non-critical errors
- User-friendly error messages in UI functions
- Structured logging for debugging
- Atomic operations to prevent data corruption

### Testing Considerations
- All functions include comprehensive error paths
- Async functions designed for proper testing
- Mock-friendly interfaces
- Deterministic behavior for test validation

### Performance Characteristics
- Efficient string operations
- Minimal memory overhead
- Async I/O for scalability
- Proper resource cleanup